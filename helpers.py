import re

def getTriggerArgs(trigger_args):
    # Trigger examples:
    # ['cron', '* * * * * *']
    # ['interval', 'minutes', '6']
    try:
        targs = {}
        trigger_type = trigger_args[0]
        targs['trigger'] = trigger_type
        if(trigger_type == 'cron'):
            targs['cron'] = CronTrigger.from_crontab(trigger_args[1])
        elif(trigger_type == 'interval'):
            targs[trigger_args[1]] = int(trigger_args[2])
        elif(trigger_type == 'date'):
            targs['run_date'] = trigger_args[1]
        return targs
    except:
        return {}


def get_array_actions(actions):
    # Gets actions list in format: ['module:licor:on', 'module:extp:off']
    # Verify format with regex and converts it to tuples and append it to list so it is saved in correct format
    array_actions = []
    regex = "^((module|wait):\w+:\w+)$|^(mode:\w+)$|^(analyse)$"
    e = ValueError("Invalid action format: " + str(actions))
    for a in actions:
        if not re.match(regex, a):
            raise e
        action = a.split(':')
        for i in range(3):
            if(len(action) <= i):
                action.append(None)
        array_actions.append(action)
    if not array_actions:
        raise e
    return array_actions
