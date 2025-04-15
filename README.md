# RBMIC Biological HE and Fluorescence Image Registration Software
## 1. Introduction
The RBMIC Biological HE and Fluorescence Image Registration Software is designed for cell-level alignment of Hematoxylin & Eosin (HE) and fluorescence images. Written in Python, this tool allows users to manually mark matching cell pairs, significantly enhancing registration accuracy compared to conventional methods.
## 2. Installation
1.	Ensure Python (≥3.6) is installed on your system.
2.	Install Dependencies:
```
  	pip install opencv-python  
```
3. Download the `rbmic.zip` archive from the /code directory and unzip `rbmic.zip` to your desired directory.
4. Running:  
  Local Execution: Right-click the main program file and select "Run with Python".  
  Server Execution: Navigate to the directory via Terminal/SSH and run the program using Python commands.
   
## 3. Usage
### 3.1 Image Preprocessing 
Run `before.py`, input the paths of the two images, and enter preprocessing parameters as prompted and handles image preprocessing tasks such as adjusting the region of interest (ROI) and executing image processing functions.
```
#bash $python before.py  
```
### 3.2 Image Coordinate Clicking 
Run `image_clicker.py` for both images to mark corresponding cell coordinates and enables interactive coordinate selection and saves regions of interest (ROIs).
```
#bash $image_clicker.py
```
### 3.2 Dual-Image Registration
Run `full.py` or `full1.py`, input the image paths and the four marked coordinates to performs angle and length ratio calculations, image resizing, cropping, alignment, and image overlay for result verification.
```
#bash $python full.py
or
#bash $python full1.py
```
`full.py`: This version emphasizes fluorescence signal, making it ideal for observing fluorescence intensity and signal distribution.\
`full1.py`: This version emphasizes HE morphology, making it more suitable for observing the structural details of Hematoxylin & Eosin-stained tissue.

### 3.3 Affine Transformation 
Run `distory_image.py` with the image paths and eight edge coordinates to implements image perspective transformation and overlay visualization, featuring an interactive interface for inputting image paths and keypoint coordinates.
```
#bash $python distory_image.py
```
### 3.4 Adjustment 
If the output results cannot meet the requirements of the user, please run `image_clicker.py` again and  other next steps.
