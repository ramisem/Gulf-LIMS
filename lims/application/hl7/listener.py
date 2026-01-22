import socket, threading, re, queue
from datetime import datetime
from ihcworkflow.models import IhcWorkflow
from sample.models import Sample
from util.actions import GenericAction
from hl7.sender import send_hl7_for_cancellation
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import connection, transaction
from logutil.log import log

START_BLOCK = b'\x0b'
END_BLOCK = b'\x1c'
CARRIAGE_RETURN = b'\x0d'

message_queue = queue.Queue()


class HL7Listener:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.executor = ThreadPoolExecutor(max_workers=settings.HL7_THREADPOOL_MAX_WORKERS_LISTENER)
        self.executor_process_message = ThreadPoolExecutor(max_workers=settings.HL7_THREADPOOL_MAX_WORKERS_PROCESS_MSG)

    def create_mllp_message(self, hl7_raw):
        return START_BLOCK + hl7_raw.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN

    def generate_ack(self, code, msg_control_id):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ack_control_id = f"ACK{timestamp}"

        return (
            f"MSH|^~\\&|LIS|LAB|VitroStainer|LAB|{timestamp}||ACK^O21|{ack_control_id}|P|2.5.1\r"
            f"MSA|{code}|{msg_control_id}\r"
        )

    def handle_client(self, client_socket, address):
        log.info(f"[+] Connected by {address}")
        buffer = b""

        try:
            client_socket.settimeout(5)
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                buffer += chunk

                while START_BLOCK in buffer and END_BLOCK in buffer:
                    start = buffer.index(START_BLOCK)
                    end = buffer.index(END_BLOCK)
                    raw_message = buffer[start + 1:end]
                    buffer = buffer[end + 2:]

                    hl7_text = raw_message.decode("utf-8", errors="ignore")
                    log.info("Received HL7 Message:\n", hl7_text)

                    # Extract message control ID
                    msg_match = re.search(
                        r'MSH\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|(?P<msg_id>[^\|]+)',
                        hl7_text)

                    msg_control_id = msg_match.group('msg_id') if msg_match else 'UNKNOWN'
                    log.info(f"Extracted Message Control ID: {msg_control_id}")

                    # Send ACK immediately
                    ack_hl7 = self.generate_ack("AA", msg_control_id)
                    try:
                        client_socket.sendall(self.create_mllp_message(ack_hl7))
                    except Exception as e:
                        log.error(f"Error sending ACK: {e}")

                    # Enqueue message
                    message_queue.put(hl7_text)

                break  # Process only one message per connection
        except socket.timeout:
            log.error("Connection timed out.")
        except Exception as e:
            log.errror(f"Error in handle_client(): {e}")
        finally:
            client_socket.close()
            log.error(f"Connection closed: {address}\n")

    def start_worker(self):
        def worker():
            log.info("Worker Thread in Listener has started")
            while True:
                hl7_text = message_queue.get()
                try:
                    self.executor_process_message.submit(self.process_message, hl7_text)
                except Exception as e:
                    log.error(f"Worker error: {e}")
                finally:
                    message_queue.task_done()

        threading.Thread(target=worker, daemon=True).start()

    def process_message(self, hl7_text):

        try:
            slide_match = re.search(r"OBR\|1\|(?P<slide_id>[\w\-]+)\|", hl7_text)
            slide_id = slide_match.group("slide_id") if slide_match else None

            # Extract staining technique from OBR segment (field 5)
            obr_match = re.search(r"OBR\|1\|.*?\|.*?\|(?P<staining_technique>[^\|^]+)", hl7_text)
            staining_technique = obr_match.group("staining_technique") if obr_match else None

            action_instance = GenericAction()

            if "MSA|AA" in hl7_text and "ORC|NW" in hl7_text:
                log.info("Staining has officially STARTED.")
                self.start_staining(slide_id, action_instance)

            elif "MSA|AA" in hl7_text and "ORC|CA" in hl7_text:
                log.info("Staining has officially CANCELLED.")

            elif "ORC|OK" in hl7_text:
                log.info("Staining COMPLETED.")
                self.complete_staining(slide_id, action_instance)

            else:
                log.info("No status confirmation. Sending rejection...")
                if slide_id:
                    arr_slide_id = slide_id.split("-")
                    accession_id = arr_slide_id[0] + "-" + arr_slide_id[1]
                    self.update_staining_status(slide_id, status="Rejected")
                    send_hl7_for_cancellation(slide_id, accession_id, staining_technique)
                    log.info(f"Sent rejection message for {slide_id}")

        except Exception as e:
            log.error(f"Error in process_message(): {e}")

    def update_staining_status(self, slide_id, status):
        # This is for updating the staining status when slide is rejected for staining
        if not slide_id:
            log.info("Slide ID missing; skipping update.")
            return

        try:
            connection.ensure_connection()

            arr = slide_id.split("-")
            if len(arr) < 4:
                log.info("Invalid slide ID format:", slide_id)
                return

            accession_id = arr[0] + "-" + arr[1]
            part_no = arr[2]
            block = arr[3] if len(arr) > 4 else None
            slide_seq = arr[4] if len(arr) > 4 else arr[3]

            with transaction.atomic():
                qs = IhcWorkflow.objects.filter(
                    accession_id__accession_id=accession_id,
                    part_no=part_no,
                    block_or_cassette_seq=block,
                    slide_seq=slide_seq
                )
                updated = qs.update(
                    staining_status=status
                )

        except Exception as e:
            log.error(f"Error in update_staining_status(): {e}")
        finally:
            connection.close()

    def start_staining(self, slide_id, action_instance):

        # This is for starting the staining

        if not slide_id:
            log.info("Slide ID missing; skipping update.")
            return

        try:
            connection.ensure_connection()

            arr = slide_id.split("-")
            if len(arr) < 4:
                log.info("Invalid slide ID format:", slide_id)
                return

            accession_id = arr[0] + "-" + arr[1]
            part_no = arr[2]
            block = arr[3] if len(arr) > 4 else None
            slide_seq = arr[4] if len(arr) > 4 else arr[3]
            queryset = Sample.objects.filter(
                accession_id__accession_id=accession_id,
                part_no=part_no,
                block_or_cassette_seq=block,
                slide_seq=slide_seq
            )
            action_instance.start_staining_method(None, None, queryset)

        except Exception as e:
            log.error(f"Error in start_staining(): {e}")

        finally:
            connection.close()

    def complete_staining(self, slide_id, action_instance):
        # This is for completing staining
        if not slide_id:
            return
        arr = slide_id.split("-")
        if len(arr) < 4:
            return
        accession_id = arr[0] + "-" + arr[1]
        part_no = arr[2]
        block = arr[3] if len(arr) > 4 else None
        slide_seq = arr[4] if len(arr) > 4 else arr[3]

        queryset = Sample.objects.filter(accession_id__accession_id=accession_id,
                                         part_no=part_no,
                                         block_or_cassette_seq=block,
                                         slide_seq=slide_seq)
        action_instance.complete_staining_method(None, None, queryset)

    def start(self):
        log.info(f"HL7 Listener running on {self.host}:{self.port}")

        self.start_worker()  # Start the single consumer thread
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(settings.HL7_SERVER_BACKLOG)

        def accept_loop():
            log.info("Preparing the the listener to keep running")
            while True:
                client, addr = server.accept()
                # Submit connection handler to the thread pool
                self.executor.submit(self.handle_client, client, addr)

        threading.Thread(target=accept_loop, daemon=True).start()
