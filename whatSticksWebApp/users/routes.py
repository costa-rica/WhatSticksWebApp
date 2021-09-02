from flask import Blueprint

from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app, send_from_directory
from whatSticksWebApp import db, bcrypt, mail
from whatSticksWebApp.models import User, Post, Health_description, Health_measure
from whatSticksWebApp.users.forms import RegistrationForm, LoginForm, UpdateAccountForm, \
    RequestResetForm, ResetPasswordForm, LoginForm2
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
from whatSticksWebApp.users.utils import save_picture, send_reset_email, userPermission, \
    formatExcelHeader
import pytz
import zoneinfo

users = Blueprint('users', __name__)


@users.route("/", methods=["GET","POST"])
@users.route("/home", methods=["GET","POST"])
def home():
    
    return render_template('home.html')



@users.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form= RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            # userPermission1=userPermission(form.email.data)
            # if userPermission1[0]:
                # user=User(email=form.email.data, password=hashed_password, permission=userPermission1[1])
            # else:
            user=User(email=form.email.data, password=hashed_password, username=form.username.data)
            db.session.add(user)
            db.session.commit()
            flash(f'You are now registered! You can login.', 'success')
            return redirect(url_for('users.login'))
        else:
            flash(f'Did you mis type something? Check: 1) email is actually an email 2) password and confirm password match.', 'warning')
            return redirect(url_for('users.register'))
    return render_template('register.html', title='Register',form=form)


@users.route("/login", methods=["GET","POST"])
def login():
    # print('***in login form****')
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form = LoginForm2()
    print('request.args::::',request.args)
    email_entry=request.args.get('email_entry')
    pass_entry=request.args.get('pass_entry')
    if request.args.get('email_entry'):
        form.email.data=request.args.get('email_entry')
        form.password.data=request.args.get('pass_entry')
        print('pass_entry:::', request.args.get('pass_entry'))
    
    if form.validate_on_submit():
        print('login - form.validate_on_submit worked')
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('users.home'))
            #^^^ another good thing turnary condition ^^^
        else:
            flash('Login unsuccessful', 'danger')
    return render_template('login.html', title='Login', form=form)

    

@users.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('users.login'))



@users.route('/account', methods=["GET","POST"])
@login_required
def account():
    
    user_record=db.session.query(User).filter(User.id==current_user.id).first()
    timezone_list=zoneinfo.available_timezones()
    default_timezone=user_record.user_timezone
    
    form=UpdateAccountForm()
    if form.validate_on_submit():
        # if form.picture.data:
            # picture_file = save_picture(form.picture.data)
            # current_user.image_file = picture_file
        
        formDict = request.form.to_dict()
        current_user.user_timezone=formDict.get('user_timezone_input')
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        currentUser=User.query.get(current_user.id)

        db.session.commit()
        flash(f'Your account has been updated {current_user.email}!', 'success')
        return redirect(url_for('users.home')) #CS says want a new redirect due to "post-get-redirect pattern"
    #     post-get-redirect pattern is when browser asks are you sure you want to reload data.
    # It seems this is because the user will be running POst request on top of an existing post request
    elif request.method =='GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    #     This elif part is what i should do for preloading the DMR form with data when some already exists
    
    # if request.form.get('darkTheme'):
        # currentUser=User.query.get(current_user.id)
        # currentUser.theme='dark'
        # db.session.commit()
        
    # image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='account',  form=form,
        timezone_list=timezone_list,default_timezone=default_timezone)


@users.route('/reset_password', methods = ["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('email has been sent with instructions to reset your password','info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', legend='Reset Password', form=form)

@users.route('/reset_password/<token>', methods = ["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('users.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated! You are now able to login', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', legend='Reset Password', form=form)




@users.route('/database_page', methods=["GET","POST"])
@login_required
def database_page():

    tableNamesList= db.engine.table_names()
    legend='Database downloads'
    if request.method == 'POST':
        formDict = request.form.to_dict()
        if formDict.get('build_workbook')=="True":

            for file in os.listdir(current_app.config['FILES_DATABASE']):
                os.remove(os.path.join(current_app.config['FILES_DATABASE'], file))

            
            timeStamp = datetime.now().strftime("%y%m%d_%H%M%S")
            workbook_name=f"database_tables{timeStamp}.xlsx"
            print('reportName:::', workbook_name)
            excelObj=pd.ExcelWriter(os.path.join(current_app.config['FILES_DATABASE'], workbook_name),
                date_format='yyyy/mm/dd', datetime_format='yyyy/mm/dd')
            workbook=excelObj.book
            
            dictKeyList=[i for i in list(formDict.keys()) if i in tableNamesList]
            dfDictionary={h : pd.read_sql_table(h, db.engine) for h in dictKeyList}
            for name, df in dfDictionary.items():
                if len(df)>900000:
                    flash(f'Too many rows in {name} table', 'warning')
                    return render_template('database.html',legend=legend, tableNamesList=tableNamesList)
                df.to_excel(excelObj,sheet_name=name, index=False)
                worksheet=excelObj.sheets[name]
                start_row=0
                formatExcelHeader(workbook,worksheet, df, start_row)
                print(name, ' table added to workbook')
                # if name=='dmrs':
                    # dmrDateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                    # worksheet.set_column(1,1, 15, dmrDateFormat)
                
            print('path of reports:::',os.path.join(current_app.config['FILES_DATABASE'],str(workbook_name)))
            excelObj.close()
            print('excel object close')
            # return send_from_directory(current_user.config['FILES_DATABASE'],workbook_name, as_attachment=True)
            return redirect(url_for('users.database_page'))
        elif formDict.get('download_db_workbook'):
            return redirect(url_for('users.download_db_workbook'))
        elif formDict.get('uploadExcel'):
            formDict = request.form.to_dict()
            filesDict = request.files.to_dict()
            print('formDict:::',formDict)
            print('filesDict:::', filesDict)
            
            
            uploadData=request.files['excelFileUpload']
            excelFileName=uploadData.filename
            uploadData.save(os.path.join(current_app.config['UTILITY_FILES_FOLDER'], excelFileName))
            wb = openpyxl.load_workbook(uploadData)
            sheetNames=json.dumps(wb.sheetnames)
            tableNamesList=json.dumps(tableNamesList)

            # return redirect(url_for('users.databaseUpload',legend=legend,tableNamesList=tableNamesList,
                # sheetNames=sheetNames, excelFileName=excelFileName))
            return redirect(url_for('users.database_page'))
    return render_template('database_page.html', legend=legend, tableNamesList=tableNamesList)


@users.route("/download_db_workbook", methods=["GET","POST"])
@login_required
def download_db_workbook():
    # workbook_name=request.args.get('workbook_name')
    workbook_name = os.listdir(current_app.config['FILES_DATABASE'])[0]
    print('file:::', os.path.join(current_app.root_path, 'static','files_database'),workbook_name)
    file_path = r'D:\OneDrive\Documents\professional\20210710lifeBuddy\whatSticksWebApp\static\files_database\\'
    
    return send_from_directory(os.path.join(current_app.config['FILES_DATABASE']),workbook_name, as_attachment=True)
    
    # return send_from_directory(os.path.join(current_user.config['FILES_DATABASE']),workbook_name, as_attachment=True)
    
    # return send_from_directory(os.path.join(current_user.root_path, 'static','files_database'),"database_table.xlsx", as_attachment=True)
    # return send_from_directory('D:\\OneDrive\\Documents\\professional\\20210610kmDashboard2.0\\fileShareApp\\static\\files_database',"database_table.xlsx", as_attachment=True)


@users.route('/database_delete_data', methods=["GET","POST"])
@login_required
def database_delete_data():
    legend='Clear Tables in Database'
    dbModelsList= [cls for cls in db.Model._decl_class_registry.values() if isinstance(cls, type) and issubclass(cls, db.Model)]
    dbModelsDict={str(h)[22:-2]:h for h in dbModelsList}
    tableNameList=[h for h in dbModelsDict.keys()]
    if request.method == 'POST':
        formDict = request.form.to_dict()
        if formDict.get('removeData'):
            print('formDict::::',formDict)
            for tableName in formDict.keys():
                if tableName in tableNameList:
                    db.session.query(dbModelsDict[tableName]).delete()
                    db.session.commit()
            flash(f'Selected tables succesfully deleted', 'success')
    return render_template('database_delete_data.html', legend=legend, tableNameList=tableNameList)


@users.route('/database_upload', methods=["GET","POST"])
@login_required
def database_upload():
    tableNamesList=json.loads(request.args['tableNamesList'])
    sheetNames=json.loads(request.args['sheetNames'])
    excelFileName=request.args['excelFileName']
    legend='Upload Excel to Database'
    uploadFlag=True
    # if request.method == 'POST':
        
        # formDict = request.form.to_dict()
        # if formDict.get('appendExcel'):
            # wb=os.path.join(current_app.root_path, 'static', excelFileName)
            # for sheet in sheetNames:                
                # sheetUpload=pd.read_excel(wb,engine='openpyxl',sheet_name=sheet)
                # if sheet=='dmrs':
                    # sheetUpload["dmrDate"] = pd.to_datetime(sheetUpload["dmrDate"]).dt.strftime('%Y-%m-%d')
                # if sheet=='shifts':
                    # sheetUpload["shiftDate"] = pd.to_datetime(sheetUpload["shiftDate"]).dt.strftime('%Y-%m-%d')
                # if sheet=='post':
                    # sheetUpload=sheetUpload.replace(r'_x000D_','', regex=True) 
                # try:
                    # sheetUpload.to_sql(formDict.get(sheet),con=db.engine, if_exists='append', index=False)
                # except IndexError:
                    # pass
                # except:
                    # os.remove(os.path.join(current_app.root_path, 'static', excelFileName))
                    # uploadFlag=False
                    # flash(f"""Problem uploading {sheet} table. Check for uniquness make 
                        # sure not duplicate ids are being added.""", 'warning')
                    # return render_template('database_upload.html',  legend=legend,
                        # tableNamesList=tableNamesList, sheetNames=sheetNames,uploadFlag=uploadFlag)
                        
            # os.remove(os.path.join(current_app.root_path, 'static', excelFileName))
            # print(excelFileName,' should be removed from static/')
            # flash(f'Table(s) successfully uploaded to database!', 'success')

            # return render_template('database_upload.html',  legend=legend,
                # tableNamesList=tableNamesList, sheetNames=sheetNames,uploadFlag=uploadFlag)
                
    return render_template('database_upload.html',legend=legend,tableNamesList=tableNamesList,
                sheetNames=sheetNames, excelFileName=excelFileName,uploadFlag=uploadFlag)