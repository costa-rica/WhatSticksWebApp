from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app
from whatSticksWebApp import db, bcrypt, mail
from whatSticksWebApp.models import Post, User

from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from datetime import datetime, date, time
from sqlalchemy import func

import pandas as pd
import io
from wsgiref.util import FileWrapper
import xlsxwriter
from flask_mail import Message

#Kinetic Metrics, LLC
def userPermission(email):
    kmPermissions=['nickapeed@yahoo.com','test@test.com',
        'emily.reichard@kineticmetrics.com']
    if email in kmPermissions:
        return (True,'1,2,3,4,5,6,7,8')
    
    return (False,)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename) #splitext returns two values file name w/out ext, extension
#     f_name, f_ext = simply says put the first part in f_name and the second value in f_ext
# convention of an unused variable in coding is to use and "_". so this was f_name, but as Corey shared we're
# not using that variable
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    # app.root_path gives us full path up to our package directory. I think 'app' since well app is found
#    somewhere between run.py and __init__.py

    # code below uses Pillow (imported as PIL above) to resize the picture. Since the image will just be a small thumb
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='ricacbc@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''
    mail.send(msg)


#return excel files formatted
def formatExcelHeader(workbook,worksheet, df, start_row):
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'align':'center',
        'border': 0})
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(start_row, col_num, value,header_format)
        width=len(value)+1 if len(value)>8 else 8
        worksheet.set_column(col_num,col_num,width)