from .thread_seq_filter import reset_thread_seq


class ResetThreadSeqMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # reset at beginning of request so sequence starts at 1 per request
        reset_thread_seq()
        return self.get_response(request)
