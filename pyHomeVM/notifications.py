# coding=utf-8
import urllib2
import urllib
import smtplib
import time
import os
import logging
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from datetime import timedelta
from datetime import datetime
from CONSTANTS import CONSTANTS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(CONSTANTS['log_file_path'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_mail_report(mail_message, email):
    """Function that sends an html report through email.

    input: mail_message as string path as string
    output: None
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Report of {}'.format(time.strftime("%d/%m/%Y"))
    msg['From'] = email['from']
    msg['To'] = email['to']
    converted = MIMEText(mail_message, 'html')
    msg.attach(converted)
    try:
        server = smtplib.SMTP(email['server_address'])
    except Exception:
        logger.info(traceback.format_exc())
    finally:
        server.ehlo()
        server.starttls()
        server.login(email['username'], email['password'])
        server.sendmail(email['from'], email['to'], msg.as_string())
        server.quit()


def send_mail_log(logfile, email, html):
    """Function that sends the logfile through email.

    input:logfile path as string
    output:None
    """
    logger.info('sending logfile')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Logs du {}'.format(time.strftime("%d/%m/%Y"))
    msg['From'] = email['from']
    msg['To'] = html['company_mail']
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
    except Exception:
        logger.info(traceback.format_exc())
    finally:
        server.ehlo()
        server.starttls()
        server.login(email['username'], email['password'])
        server.sendmail(email['from'], html['company_mail'], msg.as_string())
        logger.info('email report sent')
        server.quit()


def send_sms_notification(sms):
    """Function that sends an sms alert.

    Used to prompt the user to connect/turn on the media center
    input: sms_text as string
    output: None
    """
    if(time.strftime("%H") < sms['scheduled_time'].split(':')[0]):
        send_datetime = time.strftime("%Y-%m-%dT{}:00Z".format(sms['scheduled_time']))
        print('today')
    else:
        send_datetime = datetime.now() + timedelta(days=1)
        send_datetime = send_datetime.strftime(
            "%Y-%m-%dT{}:00Z".format(sms['scheduled_time']))
        logger.info('sms will be sent tomorrow')
    sms_text = ("Le NAS veut transférer des fichier sur le media center. "
                "Veuillez allumer le media center svp".decode('utf-8'))
    http_req = "{}?user={}&password={}&api_id={}&to={}&text={}&scheduled_time={}".format(
        sms['server_address'],
        sms['username'],
        sms['password'],
        sms['api_id'],
        sms['to'],
        send_datetime,
        urllib.pathname2url(sms_text))
    req = urllib2.Request(http_req)
    urllib2.urlopen(req)
