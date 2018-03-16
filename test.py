import functools


def with_log(func):
    @functools.wraps(func)
    def test_log(*args, **kwargs):
        print('LOG: Running job "%s"' % func.__name__)

        try:
            result = func(*args, **kwargs)
            status = "Completed"
        except Exception as e:
            status = "Failed: "+ str(e)
            result = None

        print('LOG: Job %s' % status)
        return result


    return test_log

@with_log
def job():
    """
    TEST JOB DOC
    """
    # return print("JOBBING")
    raise ValueError("ENTRO ERROR")

job()
