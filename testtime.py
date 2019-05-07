from datetime import datetime, timedelta

time1 = datetime.now().replace(second=0)
time2 = datetime.now() + timedelta(minutes=5)

print(str(time1 - time2).split(',')[1])
