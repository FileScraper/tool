
# **FileScraper**
**FileScraper:** An advanced carver for encoded file fragments

<p align="center">
     <img alt="sampleGUIscreenshot" src="./images/SampleScreenshot.png" width="500">
</p>


## Features
* Four modes of operation:  </br>
&ensp; 1) JPEG file fragment carving <br />
&ensp; 2) Disk/Memory image carving <br />
&ensp; 3) Network packet capture (pcap files) carving <br />
&ensp; 4) Validates if a data segment is JPEG encoded data <br />

* Extracts any Huffman code tables encountered in the file fragment and saves them in a dictionary.

* Displays extracted image in the GUI window

* **[Upcoming]** The support for recovery of H.264 file fragments will be added next.

## How to use
This project was tested on Windows 10 and has two parts, a CLI program (mostly for experimenting) and a GUI. The GUI has been compiled and can be executed from the bin folder. To use it follow the following steps:
* Select one of the four operation modes 
* Select input file path (e.g., choose raw_dragon from Sampledata folder given in this repository)
* Click on Run
* View the successfully carved file fragment(s) rendered in the application window


## Sample data
The Sample Data folder contains a sample JPEG file fragment (raw_dragon). A test disk image-containing the DFRWS’07 file carving challenge-can be obtained [here](http://old.dfrws.org/2007/challenge/dfrws-2007-challenge.zip).


## Resources
Please cite to following papers if you use this tool for academic purpose;
* E. Altinisik, and H. T. Sencar, “[Automatic Generation of H. 264 Parameter Sets to Recover Video File Fragments](https://ieeexplore.ieee.org/document/9568891)”, IEEE Transactions on Information Forensics and Security, vol. 16, pp. 4857-4868, 2021.

* E. Uzun and H. T. Sencar, “[JpgScraper: An Advanced Carver for JPEG Files](https://doi.org/10.1109/TIFS.2019.2953382)”, IEEETransactions on Information Forensics and Security, 2019.

* E. Uzun and H. T. Sencar, “[Carving orphaned jpeg file fragments](https://www.researchgate.net/publication/275044127_Carving_Orphaned_JPEG_File_Fragments)”, IEEETransactions on Information Forensics and Security, vol. 10, no. 8, pp.1549–1563, 2015.
