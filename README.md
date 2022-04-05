# PDF-to-Audiobook
Here is the code and model to convert pdf books into audiobook, this is developed using Python and detectron2 Layout model (Publaynet) model is finetuned on custom dataset and used to extract only required text from the layout of pdf. and then all the extracted text are converted into audio file using google speech to text.

## MODEL USED
Detectron2 Publaynet model fine tuned on Custom Dataset
Model was tranined using 1000 labelled  images with 9 labels i.e, text, title, figure, table, useless_text, reference, figure_text, table_text, list

## Dataset Information

you can download labeled dataset from the link below
https://drive.google.com/drive/folders/1dOpaw1lZ8kKvSwTkoLnSS6AbpEwE5lTV?usp=sharing

## How to Use

Run pdf2audiobook.py, UI will popup to select pdf files and path where to save audio file.
version2.py will give text files as output which you can correct if there are any errors and then convert it into Audio.
version2.py is using simple gtts and pdf2audiobook.py is using google cloud speech to text, so please provide cloud credentials for make it to work.
