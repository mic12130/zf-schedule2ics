import os
import json
import datetime
import pytz
from dateutil.relativedelta import relativedelta
from ics import Calendar, Event
from ics.alarm.display import DisplayAlarm
from ics.grammar.parse import ContentLine

class Course(object):

    def __init__(self, course_id, course_type, course_name,
                 seq_range, week_range,
                 class_name, instructor, instructor_rank, classroom,
                 seq_start, seq_end, week_start, week_end, day_of_week,
                 hours_week, hours_total, hours_parts, points):
        self.course_id = course_id
        self.course_type = course_type
        self.course_name = course_name
        self.seq_range = seq_range
        self.week_range = week_range
        self.class_name = class_name
        self.instructor = instructor
        self.instructor_rank = instructor_rank
        self.classroom = classroom
        self.seq_start = seq_start
        self.seq_end = seq_end
        self.week_start = week_start
        self.week_end = week_end
        self.day_of_week = day_of_week
        self.hours_week = hours_week
        self.hours_total = hours_total
        self.hours_parts = hours_parts
        self.points = points

class CourseTime(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

FIRST_WEEK_MONDAY = datetime.date(2021, 8, 30)

COURSE_TIME_MAP = {
    1: CourseTime('08:30', '09:10'),
    2: CourseTime('09:15', '09:55'),
    3: CourseTime('10:05', '10:45'),
    4: CourseTime('10:50', '11:30'),
    5: CourseTime('13:30', '14:10'),
    6: CourseTime('14:15', '14:55'),
    7: CourseTime('15:05', '15:45'),
    8: CourseTime('15:50', '16:30'),
    9: CourseTime('18:40', '19:20'),
    10: CourseTime('19:25', '20:05'),
    11: CourseTime('20:10', '20:50'),
}

courses = []

f = open(os.path.expanduser('~/Desktop/schedule.json'), 'r')
j = json.loads(f.read())

for course in j['kbList']:
    course_id = course['kch']
    course_type = course['skfsmc']
    course_name = course["kcmc"]
    class_name = course["jxbmc"]
    instructor = course["xm"]
    instructor_rank = course["zcmc"] if 'zcmc' in course else ''
    classroom = course["cdmc"]
    week_range = course["zcd"].replace('周', '')
    seq_range = course["jc"].replace('节', '')
    day_of_week = course["xqj"]
    hours_week = course['zhxs']
    hours_total = course['zxs']
    hours_parts = course['kcxszc']
    points = course['xf']

    # handle week range
    week_dash_index = week_range.find('-')
    if week_dash_index == -1:
        week_start = week_end = week_range
    else:
        week_start = week_range[:week_dash_index]
        week_end = week_range[week_dash_index + 1:]

    # handle sequence range
    seq_dash_index = seq_range.find('-')
    if seq_dash_index == -1:
        seq_start = seq_end = seq_range
    else:
        seq_start = seq_range[:seq_dash_index]
        seq_end = seq_range[seq_dash_index + 1:]

    courses.append(Course(course_id, course_type, course_name,
                          seq_range, week_range,
                          class_name, instructor, instructor_rank, classroom,
                          int(seq_start), int(seq_end), int(
                              week_start), int(week_end), int(day_of_week),
                          hours_week, hours_total, hours_parts, points))

c = Calendar()

for course in courses:
    tz = pytz.timezone('Asia/Shanghai')
    date = FIRST_WEEK_MONDAY + \
        relativedelta(days=(course.week_start - 1)
                      * 7 + (course.day_of_week - 1))
    # take the start of the first sequence
    time_start = datetime.datetime.strptime(
        COURSE_TIME_MAP[course.seq_start].start, '%H:%M').time()
    # take the end of the last sequence
    time_end = datetime.datetime.strptime(
        COURSE_TIME_MAP[course.seq_end].end, '%H:%M').time()
    # combine
    datetime_start = datetime.datetime.combine(date, time_start).astimezone(tz)
    datetime_end = datetime.datetime.combine(date, time_end).astimezone(tz)
    # instructor field
    intructor_field = course.instructor + ('（{}）'.format(course.instructor_rank) if course.instructor_rank != '' else '')
    
    title = '{} @ {}'.format(course.course_name, course.classroom)
    info_basic = '课程 ID：{}\n课程类型：{}\n课程名称：{}'.format(
        course.course_id, course.course_type, course.course_name)
    info_time = '课程节数：{} 节\n课程周数：{} 周'.format(
        course.seq_range, course.week_range,)
    info_teaching = '教学班名称：{}\n教师：{}\n课室：{}'.format(
        course.class_name, intructor_field, course.classroom)
    info_others = '周学时：{}\n总学时：{}\n学时组成：{}\n学分：{}'.format(
        course.hours_week, course.hours_total, course.hours_parts, course.points)
    info = '#基本信息\n{}\n\n#时间\n{}\n\n#教学\n{}\n\n#其它\n{}'.format(
        info_basic, info_time, info_teaching, info_others)

    ics_day_map = {
        1: 'MO',
        2: 'TU',
        3: 'WE',
        4: 'TH',
        5: 'FR',
        6: 'SA',
        7: 'SU'
    }

    e = Event()
    e.name = title
    e.description = info
    e.begin = datetime_start
    e.end = datetime_end
    # show alarm 30 mins prior to the event
    e.alarms = [DisplayAlarm(trigger=datetime.timedelta(minutes=-30))]

    # recurring event is not supported in ics-py, so create it as a custom property
    # COUNT should be the total times that the event being triggered, including the first time
    if course.week_start != course.week_end:
        rrule_value = 'FREQ=WEEKLY;WKST=MO;COUNT={};INTERVAL=1;BYDAY={}'.format(
            course.week_end - course.week_start + 1,
            ics_day_map[course.day_of_week])
        e.extra.append(ContentLine(name='RRULE', value=rrule_value))

    c.events.add(e)

with open('export.ics', 'w') as f:
    f.writelines(c)
