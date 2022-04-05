import pdf2image
from pdf2image import convert_from_bytes
import time
# import tensorflow as tf
import cv2
import os
import glob
from PIL import Image
import numpy as np
import layoutparser as lp
# from google.cloud import texttospeech
import tempfile
# import io
from pydub import AudioSegment
from moviepy.editor import concatenate_audioclips, AudioFileClip
import os
import pyttsx3 as tts
import PySimpleGUI as sg
import traceback
import re


ocr_agent = lp.TesseractAgent(languages='eng')
index = 0

text_final = ''

custom_label_map = {0: "text", 1: "title", 2: "figure", 3: "table", 4: "useless_text", 5: "reference", 6: "figure_text", 7: "table_text", 8: "list"}

# model = lp.Detectron2LayoutModel(
#             config_path ='lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config', # In model catalog
#             label_map   = {0: "Text", 1: "Title", 2: "List", 3:"Table", 4:"Figure"}, # In model`label_map`
#         )
model = lp.Detectron2LayoutModel(r"/home/spsdevil/Desktop/pdf2audiobook/fine_tuned_model/config_final_30k.yaml",
                                 r"/home/spsdevil/Desktop/pdf2audiobook/fine_tuned_model/model_final_30k.pth",
                                 label_map=custom_label_map,
                                 extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8]
                                )


def clean_text(text, brackets="()[]"):
    count = [0] * (len(brackets) // 2) # count open/close brackets
    saved_chars = []
    for character in text:
        for i, b in enumerate(brackets):
            if character == b: # found bracket
                kind, is_close = divmod(i, 2)
                count[kind] += (-1)**is_close # `+1`: open, `-1`: close
                if count[kind] < 0: # unbalanced bracket
                    count[kind] = 0  # keep it
                else:  # found bracket to remove
                    break
        else: # character is not a [balanced] bracket
            if not any(count): # outside brackets
                saved_chars.append(character)
    return ''.join(saved_chars)

def main(pdf_paths, progress_bar, first_page, last_page, output_path_txt):
    # DECLARE CONSTANTS
    for pdf_path in pdf_paths:
        text_final = ''
        text_separated = ''
        # PDF_PATH = "use_case_4.pdf"
        PDF_PATH = pdf_path
        # output_mp3_path = "/home/spsdevil/Desktop/pdf2audiobook/output_mp3/final_output.mp3"
        print(last_page)
        if last_page == 'None':
            print("here")
            last_page = None

        images = convert_from_bytes(open(PDF_PATH, 'rb').read(), first_page = first_page, last_page = last_page)

        image = np.array(images)

        audio_id = 0
        index = 1
        #loop through each page
        for image in images:
            # ocr_agent = lp.ocr.TesseractAgent()
            
            image = np.array(image)
            
            layout = model.detect(image)

            color_map = {
                        'text': 'red',
                        'title': 'blue',
                        'list': 'green',
                        'table': 'purple',
                        'figure': 'pink',
                        'useless_text': 'yellow',
                        'reference': 'magenta',
                        'figure_text': 'cyan',
                        'table_text': 'white'
                        }

            text_blocks = lp.Layout([b for b in layout if b.type=='title' or b.type == 'text' or b.type == 'list'])
            image_width = len(image[0]) 

            # Sort element ID of the left column based on y1 coordinate
            left_interval = lp.Interval(0, image_width/2, axis='x').put_on_canvas(image)
            left_blocks = text_blocks.filter_by(left_interval, center=True)._blocks
            left_blocks.sort(key = lambda b:b.coordinates[1])

            # Sort element ID of the right column based on y1 coordinate
            right_blocks = [b for b in text_blocks if b not in left_blocks]
            right_blocks.sort(key = lambda b:b.coordinates[1])

            # Sort the overall element ID starts from left column
            text_blocks = lp.Layout([b.set(id = idx) for idx, b in enumerate(left_blocks + right_blocks)])

            # i = lp.draw_box(image, text_blocks, box_width=2, show_element_id=True, show_element_type=True, color_map=color_map)
            # i.save('pdf_page_img/pdf_page_' + str(index) + '.jpg', "JPEG")
            # index += 1
            progress_bar.UpdateBar(audio_id + 10)
            audio_id += 10
            for block in text_blocks:
                # Crop image around the detected layout
                segment_image = (block
                                .pad(left=15, right=15, top=5, bottom=5)
                                .crop_image(image))
                
                # Perform OCR
                text = ocr_agent.detect(segment_image)
                text = clean_text(text, brackets="()[]{}")
                text_ls = [txt for txt in text.split('-\n')]
                text_clean = ''.join(text_ls)

                # Save OCR result
                block.set(text=text_clean, inplace=True)
            for txt in text_blocks:
                text_final += '\n' + txt.text
            text_separated += '\n' + '-------------------------' + '\n' + text_final
            text_final = ''
        
        pdf_name = str(pdf_path.split("/")[-1].split('.')[0])
        final_txt_path = output_path_txt + '/' + pdf_name + '.txt'
        f = open(final_txt_path, 'w')
        f.write(text_separated)
        f.close()
    return text_separated

def save_txt_file(txt, path):
    f = open(path, 'w')
    f.write(txt)
    f.close()

def convert(txt, path):
    engine = tts.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.7)
    engine.save_to_file(txt, path)
    engine.runAndWait()

def convert_from_text(txt_path, path):
    f = open(txt_path,"r")
    txt = f.read()
    engine = tts.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.7)
    path = str(path)
    print(path)
    engine.save_to_file(txt, path)
    # engine.say(txt)
    engine.runAndWait()
    f.close()

sg.theme("DarkTeal2")
layout = [[[sg.T("")], [sg.Text("Choose pdf file: "), sg.Input(), sg.FilesBrowse(key="-IN1-")]],
          [sg.T("")], [sg.Text("Choose text file: "), sg.Input(), sg.FileBrowse(key="text_file")],
          [sg.T("")], [sg.Text("Choose output folder for text file: "), sg.Input(key="-IN2-" ,change_submits=True), sg.FolderBrowse(key="-IN3-")],
          [sg.T("")], [sg.Text("Choose output folder for mp3 file: "), sg.Input(key="-IN4-" ,change_submits=True), sg.FolderBrowse(key="-IN5-")],
          [sg.Text('Select First Page',size=(30, 1), font='Lucida',justification='left')],
          [sg.Combo([i for i in range(1,100)], size=(10,5),default_value= 1, key='first_page', enable_events=True)],
          [sg.Text('Select Last Page',size=(30, 1), font='Lucida',justification='left')],
          [sg.Combo([i for i in range(1,100)], size=(10,5), default_value = 'None', key='last_page', enable_events=True)],
          [sg.Button('Extract'), sg.Button('Save Text File'), sg.Button('Convert and Save'), sg.Button("Convert from text file"), sg.Exit()],
          [sg.ProgressBar(800, orientation='h', size=(100,20), key='progressbar')]]

window = sg.Window('PDF to Audiobook Converter', layout)
progress_bar = window['progressbar']

while True:
    event, values = window.read()
    if event == 'Save Text File':
        try:
            output_path = values["-IN3-"] + "/" + str(values["-IN1-"].split("/")[-1]).split('.')[0] + ".txt"
            save_txt_file(text_file, output_path)
            sg.popup("Text file saved, please select text file and click on convert from text file")
        except Exception as e:
            tb = traceback.format_exc()
            sg.popup_error(f'AN EXCEPTION OCCURRED!', e, tb)
    elif event in (sg.WIN_CLOSED, 'Exit'):  # Exit button or close button pressed
        break
    elif event == 'Extract':
        paths_stacked = values["-IN1-"]
        sep_path = paths_stacked.split(";")
        out_path = values["-IN3-"]
        text_file = main(sep_path, progress_bar, values["first_page"], values["last_page"], out_path)
        progress_bar.UpdateBar(800)
        sg.popup("Succesfully Converted to text file, please click on save text button to save text file and edit, after that click on convert from text file to convert to mp3 or if you want it directly converted, click on convert button")
    elif event == 'Convert and Save':
        try:
            output_path = values["-IN5-"] + "/" + str(values["-IN1-"].split("/")[-1]).split('.')[0] + ".mp3"
            convert(text_file, output_path)
            sg.popup("mp3 file saved to the output")
        except Exception as e:
            tb = traceback.format_exc()
            sg.popup_error(f'AN EXCEPTION OCCURRED!', e, tb)
    elif event == 'Convert from text file':
        try:
            output_path = values["-IN5-"] + "/" + str(values["-IN1-"].split("/")[-1]).split('.')[0] + ".mp3"
            text_file_path = values["text_file"]
            convert_from_text(text_file_path, output_path)
            sg.popup("mp3 file saved to the output")
        except Exception as e:
            tb = traceback.format_exc()
            sg.popup_error(f'AN EXCEPTION OCCURRED!', e, tb)
window.close()