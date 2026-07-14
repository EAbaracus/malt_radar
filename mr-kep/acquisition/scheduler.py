class Scheduler:
    def __init__(self, queue, rate_limiter):
        self.queue = queue
        self.rate_limiter = rate_limiter
        
    def next_job(self):
        pending = self.queue.get_pending()
        for job in pending:
            if self.rate_limiter.can_request(job["source_id"]):
                return job
        return None
