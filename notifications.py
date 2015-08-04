
import urllib2
import urllib
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import *



def sendMailNotification(mail_message):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Rapport du {}'.format(time.strftime("%d/%m/%Y"))
    msg['From'] = mail_fromaddr
    msg['To'] = mail_toaddrs
    converted = MIMEText(mail_message,'html')
    msg.attach(converted)
    try:
        server = smtplib.SMTP(mail_server_addr)
    except:
        pass
    finally:
        #print('server OK')
        server.set_debuglevel(True)
        server.login(mail_username,mail_password)
        server.sendmail(mail_fromaddr, mail_toaddrs, msg.as_string())
        server.quit()



def sendSmsNotification(sms_text):
    http_req = "{}?user={}&password={}&api_id={}&to={}&text={}".format(sms_path, sms_user, sms_password, sms_api_id, sms_to, urllib.pathname2url(sms_text))
    req = urllib2.Request(http_req)
    urllib2.urlopen(req)