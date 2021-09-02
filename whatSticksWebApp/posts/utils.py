import os
from PIL import Image
import datetime
from flask import current_app

def saveScreenshot(form_picture):
    timeStamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    screenshotName=f"screenshot{timeStamp}"
    
    # random_hex = secrets.token_hex(8)
    _, fileExtension = os.path.splitext(form_picture.filename) #splitext returns two values file name w/out ext, extension
#     f_name, fileExtension = simply says put the first part in f_name and the second value in fileExtension
# convention of an unused variable in coding is to use and "_". so this was f_name, but as Corey shared we're
# not using that variable
    screenshotFileName = screenshotName + fileExtension
    picture_path = os.path.join(current_app.root_path, 'static/screenshots', screenshotFileName)
    print('savScreenshot::::', picture_path)
    # app.root_path gives us full path up to our package directory. I think 'app' since well app is found
#    somewhere between run.py and __init__.py

    # code below uses Pillow (imported as PIL above) to resize the picture. Since the image will just be a small thumb
    output_size = (1250, 1250)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return screenshotFileName