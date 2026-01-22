# hl7/sender.py
import socket
from datetime import datetime
from django.conf import settings
from accessioning.models import Accession
from logutil.log import log

START_BLOCK = b'\x0b'
END_BLOCK = b'\x1c'
CARRIAGE_RETURN = b'\x0d'


def create_mllp_message(hl7_raw):
    return START_BLOCK + hl7_raw.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN


def send_single_hl7(slide_id, accession_id, staining_technique):

    # This is for sending hl7 message for starting the staining process
    log.info("Slide Id: " + slide_id + ",Accession Id: " + accession_id + ",Staining Technique: " + staining_technique)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    accession = Accession.objects.get(accession_id=accession_id)
    if accession:
        patient = accession.patient_id
        patient_first_name = patient.first_name or ""
        patient_last_name = patient.last_name or ""
        mrn = patient.mrn or "UNKNOWN"
        patient_name_hl7 = f"{patient_last_name}^{patient_first_name}"

        referring_doctor = accession.doctor
        referring_doctor_name = ""
        if referring_doctor:
            referring_doctor_first_name = referring_doctor.first_name
            referring_doctor_last_name = referring_doctor.last_name
            referring_doctor_name = f"{referring_doctor_last_name}^{referring_doctor_first_name}"

        reporting_doctor = accession.reporting_doctor
        reporting_doctor_name = ""
        if reporting_doctor:
            reporting_doctor_first_name = reporting_doctor.first_name
            reporting_doctor_last_name = reporting_doctor.last_name
            reporting_doctor_name = f"{reporting_doctor_last_name}^{reporting_doctor_first_name}"

        hl7_message = (
            f"MSH|^~\\&|LIS|Gulf|ANATRAZ|Gulf|{timestamp}||OML^O21|MSG{slide_id[-4:]}{timestamp[-4:]}|P|2.5.1|\r"
            f"PID|1|{mrn}|{mrn}||{patient_name_hl7}||||||\r"
            f"PV1|1|I|||||{referring_doctor_name}||{reporting_doctor_name}|\r"
            f"SPM|1|{slide_id}^A|{accession_id}^|T28000^LUNG (NEOM)|||||\r"
            f"SAC||{accession_id}^|{accession_id}-A-1^1|{accession_id}-A^A||T28000^LUNG (NEOM)||||||\r"
            f"ORC|NW|{accession_id}|||||||{timestamp}|\r"
            f"OBR|1|{slide_id}|1|{staining_technique}^{staining_technique}|N|{timestamp}|||||||M||||||||||||||||||||\r"
        )
        log.info("HL7 Message: " + str(hl7_message))
        try:
            with socket.create_connection((settings.HL7_STAINER_IP, settings.HL7_STAINER_PORT), timeout=settings.HL7_TIMEOUT) as sock:
                sock.sendall(create_mllp_message(hl7_message))
                ack = sock.recv(4096).decode("utf-8", errors="ignore")
                return ack
        except Exception as e:
            log.error("HL7 send failed:", e)
            return f"ERROR: {e}"

def send_hl7_for_cancellation(slide_id, accession_id, staining_technique):
    log.info("Slide Id: " + slide_id + ",Accession Id: " + accession_id + ",Staining Technique: " + staining_technique)
    if slide_id and accession_id:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        accession = Accession.objects.get(accession_id=accession_id)
        if accession:
            patient = accession.patient_id
            patient_first_name = patient.first_name or ""
            patient_last_name = patient.last_name or ""
            mrn = patient.mrn or "UNKNOWN"
            patient_name_hl7 = f"{patient_last_name}^{patient_first_name}"

            referring_doctor = accession.doctor
            referring_doctor_name = ""
            if referring_doctor:
                referring_doctor_first_name = referring_doctor.first_name
                referring_doctor_last_name = referring_doctor.last_name
                referring_doctor_name = f"{referring_doctor_last_name}^{referring_doctor_first_name}"

            reporting_doctor = accession.reporting_doctor
            reporting_doctor_name = ""
            if reporting_doctor:
                reporting_doctor_first_name = reporting_doctor.first_name
                reporting_doctor_last_name = reporting_doctor.last_name
                reporting_doctor_name = f"{reporting_doctor_last_name}^{reporting_doctor_first_name}"

            hl7_message = (
                f"MSH|^~\\&|LIS|Gulf|ANATRAZ|Gulf|{timestamp}||OML^O21|MSG{slide_id[-4:]}{timestamp[-4:]}|P|2.5.1|\r"
                f"PID|1|{mrn}|{mrn}||{patient_name_hl7}||||||\r"
                f"PV1|1|I|||||{referring_doctor_name}||{reporting_doctor_name}|\r"
                f"SPM|1|{slide_id}^A|{accession_id}^|T28000^LUNG (NEOM)|||||\r"
                f"SAC||{accession_id}^|{accession_id}-A-1^1|{accession_id}-A^A||T28000^LUNG (NEOM)||||||\r"
                f"ORC|CA|{accession_id}|||||||{timestamp}|\r"
                f"OBR|1|{slide_id}|1|{staining_technique}^{staining_technique}|N|{timestamp}|||||||M||||||||||||||||||||\r"
            )
            log.info("HL7 Message: " + str(hl7_message))
            try:
                with socket.create_connection((settings.HL7_STAINER_IP, settings.HL7_STAINER_PORT), timeout=settings.HL7_TIMEOUT) as sock:
                    sock.sendall(create_mllp_message(hl7_message))
                    ack = sock.recv(4096).decode("utf-8", errors="ignore")
                    return ack
            except Exception as e:
                log.error("HL7 send failed:", e)
                return f"ERROR: {e}"

def send_hl7_for_staining_complete(slide_id):
    try:
        hl7_message = (
            f"MSH|^~\\&|LIS|Gulf|VitroStainer|Gulf|20221122161330||ORL^O22^ORL_O22|20221122161330880|P|2.5.1|\r"
            f"MSA|AA|2025-07-17T17:57:59.3101399+00:00||||\r"
            f"PID|1|2565230|2565230||MARTINEZ^BACHILLER^WELCOME||||\r"
            f"PV1|1|I|||||JACORTES^CORTÉS TORO^JOSÉ ANTONIO||JACORTES^CORTÉS TORO^JOSÉ ANTONIO\r"
            f"SAC|||||||20130101154520|\r"
            f"ORC|OK|22B0026180||||||||||||||||||||\r"
            f"OBR|1|{slide_id}||CDX2^CDX2|N||20250717135759||||||||||"
        )

        with socket.create_connection((settings.HL7_LISTENER_HOST, settings.HL7_LISTENER_PORT),
                                      timeout=settings.HL7_TIMEOUT) as sock:
            sock.sendall(create_mllp_message(hl7_message))
            ack = sock.recv(4096).decode("utf-8", errors="ignore")
            return ack
    except Exception as e:
        log.error("HL7 send failed:", e)
        return f"ERROR: {e}"
