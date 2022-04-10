import warnings
warnings.filterwarnings("ignore")

import glob
import os
import ffmpeg
import numpy as np
import pickle as pc
from PIL import Image
from io import BytesIO
import glob
import sys
from random import sample, randrange
import pandas as pd
#import classifier2 as cs
import nltk, re, string, collections
from nltk.util import ngrams
import math
from scipy.stats import entropy
import numpy as np
import time
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import sklearn_json as skljson

from avc_traverse import *

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))

def findRepeatedDiff(tmpImg):
    l=[0]*10
    ind=0
    retTmp=len(tmpImg)
    for i in range(100,len(tmpImg)-8):
        if np.mean(np.abs(tmpImg[i,:,:]-tmpImg[i+1,:,:]))==0:
            check=1
            for j in range(i+1,i+15):
                if np.mean(np.abs(tmpImg[j,:,:]-tmpImg[j+1,:,:]))>0:
                    check=0
            if check == 1:   
                return (i-8)
    return retTmp


def prepare_dataFromDF(df, cat_cols):
    df.fillna(-1, inplace = True)
    num_cols = df.shape[1] - 1
    features = df.columns[:num_cols]
    
    X = df[features]
    y = df.iloc[:, num_cols].values
    return X, y, features

def ngram2feature(values):
    cavcVsCab255={}
    for clm in range(12):
        cavcVsCab255[clm]=[]
    cavcVsCab255['lbl']=[]

    c=0
    for pay in [values[255],values[0],max(values)]:
        for payda in [np.mean(values),min(values)+1]:
            cavcVsCab255[c].append(pay/payda)
            c+=1

    cavcVsCab255[6].append(np.std(values))
    cavcVsCab255[7].append(entropy(values)) 

    if max(values)==values[255]:
        cavcVsCab255[8].append(1)
    else:
        cavcVsCab255[8].append(0)

    if max(values)==values[0]:
        cavcVsCab255[9].append(1)
    else:
        cavcVsCab255[9].append(0)

    cavcVsCab255[10].append(cavcVsCab255[6][-1]/np.mean(values))
    cavcVsCab255[11].append(sum(values>(np.mean(values)*1.5)))

    cavcVsCab255['lbl'].append(0)

    df=pd.DataFrame.from_dict(cavcVsCab255)
    X,y,features = prepare_dataFromDF(df,[])
    return X

def DataToFeature(data):
    esBigrams = ngrams(data, 1)
    esBigramFreq = collections.Counter(esBigrams)
    esBigramFreq=sorted(esBigramFreq.items())
    if len(esBigramFreq)==256:
        esBigramOnlyFreq=[x[1] for x in esBigramFreq]
    else:
        esBigramOnlyFreq=[]
        j=0
        for i in range(256):
            if j<len(esBigramFreq) and esBigramFreq[j][0][0]==i:
                esBigramOnlyFreq.append(esBigramFreq[j][1])
                j+=1
            else:
                esBigramOnlyFreq.append(0)

    return ngram2feature(esBigramOnlyFreq)            
         
def mul_ent(row,predic):
    if row['entropy_coding_mode_flag'] == 0:
        return row['size']*predic[0][0]
    return row['size']*predic[0][1]
    
def err2feature(errors):
    errl=[]

    for error in errors.split('\n'):
        if error.startswith('[h264 @') or error.startswith('Error'):
            try:
                errorStr=''.join([i for i in error.split(']')[1] if not i.isdigit()])
            except:
                errorStr=''.join([i for i in error if not i.isdigit()])

            if 'top block unavailable' in errorStr:
                errorStr=' top block unavailable for requested intra mode -'
                
            elif 'QP  out of range' in errorStr:
                qpV=int(error.split(']')[1].split(' ')[2])
                if qpV>-100 and qpV < 200:
                    errorStr='QP less out of range'
                else:
                    errorStr='QP more out of range'

            if 'concealing' in errorStr or 'error while decoding MB' in errorStr:
                continue

            errl.append(errorStr)
            
    return errl
    
def testClmns(sps_pps,IFrame,isFinal=0):
    tmpVideoName = os.path.join(directory,'test.h264')
    f=open(tmpVideoName,'wb')
    f.write(sps_pps)
    f.write(IFrame)
    f.close()
    
    try:
        out, err = (
        ffmpeg
        .input(tmpVideoName)
        .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
        .run(capture_stdout=True,capture_stderr=True)
        )
        try:
            err=err.decode('ascii')
        except:
            return -1
        
    except ffmpeg.Error as e:
        try:
            err=e.stderr.decode('ascii')
        except:
            return -1

    errl=err2feature(err)
    
    if  len(notFoundError.intersection(set(errl)))>0:
        reasons[0]+=1
        return -1
    
    if  len(possibleError.intersection(set(errl)))>0:
        reasons[1]+=1
        return 0

    try:
        image=Image.open(BytesIO(out))
        tmpImg = np.array(image)
    except:
        reasons[2]+=1
        return 0
    
    meanOfImage=tmpImg.mean()
    if meanOfImage==0 or (meanOfImage>125.9 and meanOfImage<126.1):
        reasons[3]+=1
        return 0
    if isFinal==1:
        search_path = os.path.join(directory,'res*.jpg')
        files=glob.glob(search_path)
        
        saveDir = os.path.join(directory,'res'+str(len(files))+'.jpg')
        
        width, height = image.size
        tmpImg = np.array(image)
        height = findRepeatedDiff(tmpImg)
        image=image.crop((0,0, width,height ))
        
        global savedFile
        savedFile = saveDir
        
        image.save(saveDir)
    return 1
            
            
dictPars={54:'transform_8x8_mode_flag',36:'entropy_coding_mode_flag',16:'log2_max_frame_num_minus4',17:'pic_order_cnt_type',
          18:'log2_max_pic_order_cnt_lsb_minus4',48:'pic_init_qp_minus26',51:'deblocking_filter_control_present_flag',
          25:'pic_width_in_mbs_minus1',30:'frame_cropping_flag', 31:'frame_crop_right_offset'}

sps_pps_file = os.path.join(dir_path,'sps_pps.pyt')
spsPps=pc.load(open(sps_pps_file,'rb'))

#modelEntropy=pc.load(open('entropyModel.pyt','rb'))
model_entropy_file = os.path.join(dir_path,'random_forest.json')
modelEntropy = skljson.from_json(model_entropy_file)

notFoundError=set([' top block unavailable for requested intra mode -',
                   ' top block unavailable for requested intra mode',
                   ' negative number of zero coeffs at  ',
                   ' cabac decode of qscale diff failed at  '])

possibleError=set([' top block unavailable for requested intra mode -',
                   ' top block unavailable for requested intra mode',
                   ' negative number of zero coeffs at  ',
                   ' mb_type  in I slice too large at  ',
                   ' left block unavailable for requested intra mode',
                   ' left block unavailable for requested intrax mode -',
                   ' left block unavailable for requested intrax mode - at  ',
                   ' out of range intra chroma pred mode'])
reasons=[0]*4
def updateCheck(s, row, value):
    if s['check']==0:
        for key in list(dictPars.values())[:7]:
            if s[key] != row[key]:
                return s['check']
        return value
    
    return s['check']

def runWidth(IFrame):
    
    dfTemp=spsPps.copy()
    
    predic=modelEntropy.predict_proba(DataToFeature(IFrame))
    dfTemp['size'] = dfTemp.apply(mul_ent, args=(predic,), axis=1)
    dfTemp=dfTemp.sort_values(by=['size'],ascending=False)


    c=0
    d=0
    check=0
    dfTemp['check']=0
    for index, row in dfTemp.iterrows():
        if row['check']==-1: #invalid
            continue
        testRow=0
        if row['check']==0: # check width
            res=testClmns(row['sps_pps_width'],IFrame) #-1 wrong core parameters, 1 found, 0 wrong width
            c+=1
            if res==-1:
                dfTemp['check']=dfTemp.apply(updateCheck, args=(row,-1,), axis=1)
            elif res==0:
                testRow=1
                dfTemp['check']=dfTemp.apply(updateCheck, args=(row,1,), axis=1)
            else:
                return c,row
            
        if row['check']==1 or testRow==1:
            res=testClmns(row['sps_pps'],IFrame) #-1 wrong core parameters, 1 found, 0 wrong width
            c+=1
            d+=1
            if res==1:
                return c,row
    return -2,0
                
            
def run(IFrame):
    c, row =runWidth(IFrame)
    if c==-2:
        return -1, ''
    
    testClmns(row['sps_pps_height'],IFrame,isFinal=1)
    return 1, row
    
    
if __name__ == "__main__":
    file=sys.argv[1]
    isFile=sys.argv[2]
# def runFile(file):
#     #directory=os.path.dirname(file)+'/frames/'
#     global directory
#     global savedFile
    savedFile=''
    directory=file+'frames'
        
#     f=open(file,'rb')
#     binaryDatas=f.read()

#     datas=binaryDatas.split(b'\x00\x00\x00\x01')

#     f.close()

#     for dataBig in datas[1:]:
#         datasLittle=dataBig.split(b'\x00\x00\x01')
#         for data in datasLittle:
#             if data.startswith(b'e') or data[0]==37:
#                 IFrame=data
               
    byte_array = file_reader(file)
    path_list = randomized_search(byte_array, 4)
    combine=False
    for NALU in path_list:
        if NALU['type']==False:
            combine=True
            directory=file+'frames'
            if not os.path.exists(directory):
                os.mkdir(directory)
                
                
            if 'video' in locals():
                tmpVideoName = os.path.join(directory,'test.h264')
                tmpOutName = os.path.join(directory,'%d.jpg')
                f=open(tmpVideoName,'wb')
                f.write(row['sps_pps_height'])
                f.write(video)
                f.close()
                os.system('ffmpeg -i "'+tmpVideoName+'" "'+tmpOutName+'"') 
                
            video=NALU['data']
            IFrame=NALU['data']
            
            tmpName = os.path.join(directory,'test.h264')
            os.system('rm -rf "'+tmpName+'"')
            
            res=0
            if 'row' in locals():
                res=testClmns(row['sps_pps_height'],IFrame,isFinal=1) 
                if isFile=='file':
                    continue
            if res==1:
                tst=1
            else:
                tst,row=run(IFrame)  
            if tst == -1:
                combine=False
                del row
                del video
            
        if combine==True:
            video+=b'\x00\x00\x00\x01'+NALU['data']

    if 'IFrame' not in locals():
        print('there is no I frame'+'\n'+ savedFile)
        
    else:
        if 'video' in locals():
            
                tmpVideoName = os.path.join(directory,'test.h264')
                tmpOutName = os.path.join(directory,'others%d.jpg')
                f=open(tmpVideoName,'wb')
                f.write(row['sps_pps_height'])
                f.write(video)
                f.close()
                os.system('ffmpeg -i "'+tmpVideoName+'" "'+tmpOutName+'"')   
                
        print('check frames in '+directory+'\n'+ savedFile)
        
        

        
        