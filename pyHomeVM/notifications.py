# coding=utf-8
import urllib2
import urllib
import smtplib
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase


def sendMailReport(mail_message, email):
    '''Function that sends an html report through email
    input: mail_message as string path as string
    output: None'''
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Report of {}'.format(time.strftime("%d/%m/%Y"))
    msg['From'] = email['from']
    msg['To'] = email['to']
    converted = MIMEText(mail_message, 'html')
    msg.attach(converted)
    try:
        server = smtplib.SMTP(email['server_address'])
    except:
        pass
    finally:
        server.login(email['username'], email['password'])
        server.sendmail(email['from'], email['to'], msg.as_string())
        server.quit()


def sendMailLog(logfile, email, html):
    '''Function that sends the logfile through email
    input:logfile path as string
    output:None'''
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Rapport du {}'.format(time.strftime("%d/%m/%Y"))
    msg['From'] = email['from']
    msg['To'] = email['to']
    converted = MIMEText('Log of the day', 'html')
    msg.attach(converted)
    log = MIMEBase('application', "octet-stream")
    log.set_payload(open(logfile, "rb").read())
    log.add_header(
        'Content-Disposition',
        'attachment; filename="{}"'.format(
            os.path.basename(logfile)))
    msg.attach(log)

    try:
        server = smtplib.SMTP(email['server_address'])
    except:
        pass
    finally:
        server.login(email['username'], email['password'])
        server.sendmail(email['from'], html['company_mail'], msg.as_string())
        server.quit()


def sendSmsNotification(sms):
    '''Function that sends an sms alert. Used to prompt the user
    to connect/turn on the media center
    input: sms_text as string
    output: None
    '''
    sms_text = ("Le NAS veut transferer des fichier sur le media center. "
                "Veuillez allumer le media center svp")
    http_req = "{}?user={}&password={}&api_id={}&to={}&text={}".format(
        sms['server_address'],
        sms['username'],
        sms['password'],
        sms['api_id'],
        sms['to'],
        urllib.pathname2url(sms_text))
    req = urllib2.Request(http_req)
    urllib2.urlopen(req)
