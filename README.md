# RBMIC Biomedical Image Registration Tool
## 1. Introduction
RBMIC (Registration-Based Merging Image Calculator) is an interactive tool for co-registration of immunohistochemistry (IHC) stained images with immunofluorescence (IF) images. The tool implements a complete pipeline from linear perspective transformation to nonlinear elastic registration, specifically designed for multimodal image alignment in medical image analysis.
## 2. Installation
1.	Ensure Python (≥3.6) is installed on your system.
2.	Install Dependencies:
```
  	pip install opencv-python numpy scipy matplotlib
```
3. Download the `pipeline.py` from the /code directory and run:
```
  	python pipeline.py
```
5. Running:  
  Local Execution: Right-click the main program file and select "Run with Python".  
  Server Execution: Navigate to the directory via Terminal/SSH and run the program using Python commands.
   
## 3. Usage
### 3.1 Image Selection:
Select hematoxylin and eosin (H&E) stained image (.jpg, .png, .bmp, .tif formats)
Select corresponding fluorescence image

### 3.2 Landmark Marking Process:
#### 3.2.1 First Stage (Global Registration):
Mark at least 3 corresponding points on HE image
Mark the same 3 corresponding points on fluorescence image
#### 3.2.1 Second Stage (Nonlinear Optimization):
Mark additional corresponding points on HE image (any number)
Mark the same points on the registered fluorescence image

### 3.2 Interactive Controls:
Left Mouse Click: Mark point
R Key: Reset current points
Enter Key: Confirm current points and proceed
S Key: Save final result
Any Other Key: Continue to next step

## 4. Technical Details
### 4.1 Registration Pipeline
1.	Initial Perspective Transformation: Global homography matrix calculation using RANSAC algorithm
2.	RBF Nonlinear Registration: Radial basis function interpolation based on landmark pairs
3.	Polynomial Transformation Alternative: Polynomial fitting when RBF fails
4.	Affine Transformation Fallback: Final safeguard when all methods fail
### 4.2 Adaptive Visualization
Marker sizes adapt to image resolution
Text label sizes and positions adjust automatically
Supports both color and grayscale images

## 5. Output
After registration completion, the program generates:
[fluorescence_filename]_reged.jpg: Registered fluorescence image
Real-time display of registration overlay

## 6. Applications
Multimodal medical image fusion
Histopathological image analysis
Fluorescence microscopy image processing
Medical image registration research

