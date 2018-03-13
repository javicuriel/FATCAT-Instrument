class Factory(object):
    def __init__(self):
        super(Factory, self).__init__()

    @abstractmethod
    def run_event(self):
        pass

    @abstractmethod
    def get_events(self):
        pass

    def set_up_scheduler(self):
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
        }
        scheduler = BackgroundScheduler(jobstores = jobstores)

        events = self.get_events()
        for event_name, time in events:
            scheduler.add_job(run_event, 'cron', second=time, id=event_name, replace_existing=True, args = [event_name])

        return scheduler
