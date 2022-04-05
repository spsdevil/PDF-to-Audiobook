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
from google.cloud import texttospeech
import tempfile
# import io
# from pydub import AudioSegment
from moviepy.editor import concatenate_audioclips, AudioFileClip
import os
from google.cloud.bigquery.client import Client
import PySimpleGUI as sg
import traceback
import re

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/spsdevil/Desktop/pdf2audiobook/pdf-2-audiobook-338519-6e86e5f94c7c.json'
bq_client = Client()

ocr_agent = lp.TesseractAgent(languages='eng')
index = 0



custom_label_map = {0: "text", 1: "title", 2: "figure", 3: "table", 4: "useless_text", 5: "reference", 6: "figure_text", 7: "table_text", 8: "list"}

# model = lp.Detectron2LayoutModel(
#             config_path ='lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config', # In model catalog
#             label_map   = {0: "Text", 1: "Title", 2: "List", 3:"Table", 4:"Figure"}, # In model`label_map`
#         )
model = lp.Detectron2LayoutModel(r"/home/spsdevil/Desktop/pdf2audiobook/fine_tuned_model/config_final_30k.yaml",
                                 r"/home/spsdevil/Desktop/pdf2audiobook/fine_tuned_model/model_final_30k.pth",
                                 label_map=custom_label_map,
                                 extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.7]
                                )

tempdir = '/home/spsdevil/Desktop/pdf2audiobook/temp_audio/'

# audio/voice config
LANGUAGE_CODE = "en-GB"
speech_client = texttospeech.TextToSpeechClient()
PITCH = {
    "title": 0.9,
    "text": -1,
    "list": -1.5
}
SPEAKING_RATE = {
    "title": 0.9,
    "text": 1,
    "list": 1.20
}
NAME = {
    "title": "en-GB-Wavenet-F",
    "list": "en-GB-Wavenet-A",
    "text": "en-GB-Wavenet-D"
}

def generate_mp3_for_ssml(id, ssml, label):

    # set text and configs
    ssml = "<speak>\n" + ssml + "</speak>\n"
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    voice = texttospeech.VoiceSelectionParams(
        language_code=LANGUAGE_CODE,
        name=NAME[label]
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=SPEAKING_RATE[label],
        pitch=PITCH[label],
    )

    # generate speech
    try:
        response = speech_client.synthesize_speech(request={"input": synthesis_input,"voice": voice,"audio_config": audio_config})
    except Exception as e:
        print("Retrying speech generation...")  # sometimes the api returns 500 error
        response = speech_client.synthesize_speech(request={"input": synthesis_input,"voice": voice,"audio_config": audio_config})

    # save a MP3 file and delete the text file
    mp3_file_name = str(id) + ".mp3"

    with open(os.path.join(tempdir, "{}".format(mp3_file_name)), "wb") as out:
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')
    print("MP3 file saved: {}".format(mp3_file_name))
 

def merge_mp3_files(audio_clip_paths):

    print("Started merging mp3 files for pdf")
    
    """Concatenates several audio files into one audio file using MoviePy
    and save it to `output_path`. Note that extension (mp3, etc.) must be added to `output_path`"""
    clips = [AudioFileClip(c) for c in audio_clip_paths]
    final_clip = concatenate_audioclips(clips)
    # final_clip.write_audiofile(output_path)
    for i in os.listdir(tempdir):
        os.remove(tempdir + i)
    return final_clip

def main(pdf_path, progress_bar, first_page, last_page):
    # DECLARE CONSTANTS
    text_final = ''
    # PDF_PATH = "use_case_4.pdf"
    PDF_PATH = pdf_path
    # output_mp3_path = "/home/spsdevil/Desktop/pdf2audiobook/output_mp3/final_output.mp3"

    images = convert_from_bytes(open(PDF_PATH, 'rb').read(), first_page = first_page, last_page = last_page)

    image = np.array(images)

    audio_id = 0
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
        
        for block in text_blocks:
            # Crop image around the detected layout
            segment_image = (block
                            .pad(left=15, right=15, top=5, bottom=5)
                            .crop_image(image))
            
            # Perform OCR
            text = ocr_agent.detect(segment_image)
            text = re.sub("[\(\[].*?[\)\]]", "", text)

            # Save OCR result
            block.set(text=text, inplace=True)
        for txt in text_blocks:
            # text_final += '\n' + txt.text
            ssml = ""
            section_break = '<break time="1.5s"/>'
            title_break = '<break time="2s"/>'
            mp3_blob_list = []
            if txt.type == 'title':
                ssml += title_break + txt.text + title_break + "\n"
            elif txt.type == 'text':
                ssml += "<p>" + txt.text + "</p>\n"
            elif txt.type == 'list':
                ssml += "<p>" + txt.text + "</p>\n"

            # generate speech for the remaining
            generate_mp3_for_ssml(audio_id, ssml, txt.type)
            audio_id += 1
        progress_bar.UpdateBar(audio_id + 10)
    # output_mp3_path = output_path_ + "final_audio.mp3"
    audio_clip_list = os.listdir(tempdir)
    audio_clip_list = [x for x in audio_clip_list if x.split('.')[-1] == 'mp3']
    audio_clip_paths = []
    while audio_clip_list:
        minimum = audio_clip_list[0]  # arbitrary number in list 
        for x in audio_clip_list: 
            if int(x.split('.')[0]) < int(minimum.split('.')[0]):
                minimum = x
        audio_clip_paths.append(tempdir + minimum)
        audio_clip_list.remove(minimum)
    mp3_file = merge_mp3_files(audio_clip_paths)
    return mp3_file
# print(text_final)
    ### mp3 ko save kaise karna hai vision api me, taki hum list me append kar k dusre wale module se concate kar paye


sg.theme("DarkTeal2")
layout = [[[sg.T("")], [sg.Text("Choose pdf file: "), sg.Input(), sg.FileBrowse(key="-IN1-")]],
          [sg.T("")], [sg.Text("Choose output folder: "), sg.Input(key="-IN2-" ,change_submits=True), sg.FolderBrowse(key="-IN3-")],
          [sg.Text('Select First Page',size=(30, 1), font='Lucida',justification='left')],
          [sg.Combo([i for i in range(1,100)], size=(10,5),default_value= 1, key='first_page', enable_events=True)],
          [sg.Text('Select Last Page',size=(30, 1), font='Lucida',justification='left')],
          [sg.Combo([i for i in range(1,100)], size=(10,5), default_value = None, key='last_page', enable_events=True)],
          [sg.Button('Convert'), sg.Button('Save'), sg.Exit()],
          [sg.ProgressBar(800, orientation='h', size=(100,20), key='progressbar')]]

window = sg.Window('PDF to Audiobook Converter', layout)
progress_bar = window['progressbar']

while True:
    event, values = window.read()
    if event == 'Save':
        try:
            output_path = values["-IN3-"] + "/" + str(values["-IN1-"].split("/")[-1]).split('.')[0] + ".mp3"
            mp3_file.write_audiofile(output_path)
        except Exception as e:
            tb = traceback.format_exc()
            sg.popup_error(f'AN EXCEPTION OCCURRED!', e, tb)
    elif event in (sg.WIN_CLOSED, 'Exit'):  # Exit button or close button pressed
        break
    elif event == 'Convert':  # Speak button pressed
        mp3_file = main(values["-IN1-"], progress_bar, values["first_page"], values["last_page"])
        progress_bar.UpdateBar(800)
        sg.popup("Succesfully Converted PDF to AUDIO, PEASE CHOOSE OUTPUT FOLDER AND CLICK ON SAVE BUTTON TO SAVE REQUIRED mp3 FILE")
window.close()