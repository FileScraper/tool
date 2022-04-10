from ast import List
import json
from struct import pack
import sys
import functools
import os
import random
import ffmpeg
import getopt
    
# EVALUATION VARIABLES
counter = 0 # number of NAL units found
extra_counter = 0
h264_counter = 0 #actual count of h264 NAL units
coverage = 1 #how much of the file gets covered

# DEBUG OPTIONS
verbose = 0 
compare_ff = 0
emul_test = 0

# TRAVERASAL VARIABLES
FALSE_POSITIVE_MARGIN = 2 #how many jumps until you ensure it is not coincidental
min_nal_size = 64
max_nal_size = 2**20
last_type = -1
last_pps_id = -1
chunk_size = 4096



def Map(fn, l) -> list:
    return list(map(fn, l))

def printf(string, **kwargs):
    if verbose: print(string, **kwargs)

# decodes data encoded in exponential golomb format (refer to 9.1 14496-part 10)
# starting at index (index), returns the decoded value along with the start point
# for next decoding as a tuple
def EG_decoder(byte_array: list, index: int):
    result, position, array_index = 0, 0, index // 8
    shift_factor = 7 - (index % 8)
    if (array_index >= len(byte_array)): return (-1, 0) #FP EG_decoding


    pos_val = (byte_array[array_index] >> shift_factor) & 0x1
    while position < 31 and not pos_val and array_index - 1 < len(byte_array):
       shift_factor = (shift_factor - 1) % 8
       if (shift_factor == 7): array_index += 1
       if (array_index >= len(byte_array)): return (-1, 0) #FP EG_decoding
       pos_val = (byte_array[array_index] >> shift_factor) & 0x1
       position += 1
 
    for i in range(position):
       shift_factor = (shift_factor - 1) % 8
       if (shift_factor == 7): array_index += 1
       if (array_index >= len(byte_array)): break #FP EG_decoding
       pos_val = (byte_array[array_index] >> shift_factor) & 0x1
       result = (result << 1) + pos_val 

    result += (2 ** position) - 1   
    return (result, index + position*2  + 1)

# given byte data (code < 0xFF) this function returns true if it encodes
# header for IDR NAL unit and false otherwise
def test_IDR(code: int) -> bool:
    if (code >> 7 == 0 and (code & 0x1F) == 5): return True;
    return False;

# given byte data (code < 0xFF) this function returns true if it encodes
# header for non-IDR NAL unit and false otherwise
def test_nonIDR(code: int) -> bool:
    if (code >> 7 == 0 and (code & 0x1F) == 1): return True;
    return False;

def test_SEI(code: int) -> bool:
    if (code >> 7 == 0 and (code & 0x1F) == 6): return True;
    return False;    

def test_startcode(code_array: int, index: int) -> bool:
    global last_pps_id
    global last_type
    if index < len(code_array) and test_IDR(code_array[index]):
        
        first_mb_in_slice, i = EG_decoder(code_array, 8*(index + 1))
        slice_type, i = EG_decoder(code_array, i)
        pps_id, i = EG_decoder(code_array, i)
        if (slice_type in (2,4,7,9) and 0 <= pps_id <= 255):
             last_type, last_pps_id = slice_type, pps_id
             return True #I-slice types
        return False

    if index < len(code_array) and test_nonIDR(code_array[index]):

        first_mb_in_slice, i = EG_decoder(code_array, 8*(index + 1))
        slice_type, i = EG_decoder(code_array, i)
        pps_id, i = EG_decoder(code_array, i)

        if (slice_type in (0,1,3,5,6,8) and 0 <= pps_id <= 255):
            
             last_type, last_pps_id = slice_type, pps_id
             return True # P/B-slice types
        return False
    #if test_SEI(code_array[index]): return True;
    return False;

# reads a video file as a binary file, storing every byte in an array
# in the sequence they occur in the file
def file_reader(file_name: str) -> list:
    byte_array, counter = [], 0
    fd = open(file_name, "rb");
    file_size = os.path.getsize(file_name)
    byte_array = fd.read()
    fd.close()
    return byte_array
    #return Map(lambda x: ord(x), byte_array)

# concats a list of byte data into a string of the corresponding ASCII chars
def str_concat(ord_list: list) -> str:
    chr_list = Map(lambda x: chr(x), ord_list)
    item = functools.reduce(lambda a, b: a + str(b), chr_list, "")
    assert(type(item) == str)
    return item

# this function returns the address of the start of the mdat box, which is done
# by matching the byte values in a 4-byte sequence to the string "mdat"
def find_mdat(byte_array: list) -> int:
    for index in range(len(byte_array)):
        if str_concat(byte_array[index: index + 4]) == "mdat":
            return index
    return -1; #on error


def get_size(index: int, byte_array: list, byte_n: int) -> int:
    sliced = byte_array[index - byte_n: index]
    return functools.reduce(lambda a,b : (a << 8) + b, sliced, 0)

# returns the size of the mdat box by casting the 4 bytes before the mdat
# signature to an int
def get_mdat_size(box_index: int, byte_array: list) -> int:
    size_slice = byte_array[box_index - 4: box_index]
    size = functools.reduce(lambda a, b: (a << 8) + b, size_slice, 0)
    print("Media Data Box size: ", size)
    if (size < 100): return -1 #change magic number
    return size

#given a path list, this function format-prints the items in the traversal
def print_traversal(path: list):
    printf("Found Possible Traversal:")
    global counter
    global extra_counter
    for items in path:
        printf("%d: " % counter, end="")
        if (test_nonIDR(items[1])): printf("non-", end="")
        else : extra_counter += 2
        printf("IDR NAL unit at index %x | size: %d bytes" % (items[0], items[2]))
        counter += 1
        extra_counter += 1
    printf("............................")

def next_NALU(byte_array: list, start_index: int, max_index: int) -> int:

    while(max_index > start_index and 
          not test_startcode(byte_array, start_index)):
        start_index += 1
    return start_index

# this function returns true if the payload of an NAL unit has emulation bytes
# (0x000000-02)
def no_emul_bytes(byte_array: list, start_index: int, max_index: int) -> bool:
    if not emul_test: return False
    for i in range(start_index, max_index - 2, 3):
        if (byte_array[i] == 0 and byte_array[i + 1] == 0 and
            byte_array[i + 2] < 3):
            return True
    return False


# this function performs a randomized search for NAL units within a video file 
# by picking a random chunk-aligned search starting position and traversing through
# the file by looking for valid NAL start codes and jumping NAL unit size to look
# for the next one, the function returns a list of all contiguous paths (sequences of NAL units
# without gaps in between), the function also updates the global variable coverage
# to indicate how much 
def randomized_search(byte_array: list, byte_n: int):
    chunk_count = len(byte_array) / chunk_size #number of [chunk_size] chunks

    #pick a random chunk within the 2% to 50% range of a video file
    #low_chunk, high_chunk = int(0.02*chunk_count), int(0.5*chunk_count)
    #random_index = random.randint(low_chunk * chunk_size, high_chunk * chunk_size)

    low = 0#random_index # search starting index
    high = len(byte_array)#(int(chunk_count * 0.98) + 1) * chunk_size # search ending index at (at 98% of file)

    path_list = []

    while (low < high):
        low = next_NALU(byte_array, low, high) #get to first potential NALU
        last = low
        path = []

        while (low < high and test_startcode(byte_array, low)):
            #loop exits if reached end of stream or the end of NALU is not
            #a start of another NALU

            size = get_size(low, byte_array, byte_n)
            end = min(high, low + size)

            if ((size < min_nal_size or size > max_nal_size or 
                 no_emul_bytes(byte_array, low, end))): #False Positive

                low = next_NALU(byte_array, low + 1, high) #go to next NALU
                last = low
                continue 
            
            path.append([low, byte_array[low], size]) # Likely to be NALU

            low += (size + byte_n) #jump to next NALU

        if (len(path) >= FALSE_POSITIVE_MARGIN): #eliminates FP paths
            print_traversal(path)
            #path_list.extend(Map(lambda lst: {"size": lst[2], "pos": lst[0]}, path))
            path_list.extend(Map(lambda lst: {"type": test_nonIDR(lst[1]),"size": lst[2], "pos": lst[0], "data": byte_array[lst[0]:lst[0]+lst[2]]}, path))
        else:
            low = last + 1 #if FP, return to last searched index + 1

    if path_list == []: return []
    return path_list
        
#extract NAL units information of a video file using ffprobe
def h264_extractor(file_name: str): 
    os.system("""ffprobe -v error \
                  -select_streams v \
                  -show_entries packet=pos,size \
                  -of json %s > temp.json""" % file_name)
    fd = open("temp.json")
    diction = json.load(fd)
    packets_array = diction["packets"]

    for item in packets_array:
        item["pos"] = int(item["pos"]) + 4
        item["size"] = int(item["size"]) - 4

    fd.close()
    return packets_array #list of {"pos": [int], "size": [int]}

# this function takes the list of identified NAL units and does statistical comparisons
# to figure out the efficacy of the search, returns a statisical metric
def get_actual_VCL(file_name: str, path_list) -> int:
    
    if not compare_ff: return -1;

    packets_array = h264_extractor(file_name)
    intersection_list = [x for x in path_list if x in packets_array] #set without FP

    if intersection_list == []: return 1.0  #no correct NALUs found

    nalu_start = min(intersection_list, key = lambda x : x["pos"])["pos"]

    #from the actual video file, identify all the NALU units that should have been found
    expected_packets = list(filter( lambda x: x["pos"] >= nalu_start, packets_array))

    #compute false positive rate as a number in [0.0, 1.0]
    fp_rate = (len(path_list) - len(intersection_list)) / len(path_list)

    #percentage of correct NALU units indentified
    percentage = ((len(intersection_list)/len(expected_packets)) * 100)

    return_metric = fp_rate #MODIFY THIS LINE TO CHANGE SUMMAR METRIC IN AVC_EVALUATE

    print("Actual number of VCL h264 NAL units: %d" % len(packets_array))
    print("Number of correct VCL NAL units identified: %d" % len(intersection_list))
    print("False positive percentage: %0.1f" % (fp_rate * 100))   
    print("Approximate Yield: %0.1f%%" % percentage)

    return return_metric 

#performs a complete traversal and evaluation for the video file [file_name]
def avc_traverse(file_name: str):
    global counter
    counter = 0

    byte_array = file_reader(file_name)
    path_list = randomized_search(byte_array, 4)
    print("Identified %d VCL NAL units" % len(path_list))
    val = get_actual_VCL(file_name, path_list)
    return val

def main():
    global verbose
    global compare_ff
    global emul_test
    if (len(sys.argv) < 2):
        print("Usage: $ python avc_traverse.py  (options) [File_name]")
        print("       -v :: prints detailed search results")
        print("       -c :: performs comparison with NALUs extracted using ffprobe")
        print("       -e :: emulation byte test, reduces FPs but much slower")
        return -1;
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "vce")
        for items in optlist:
            if items[0] == "-c": compare_ff = 1
            elif items[0] == "-v": verbose = 1
            elif items[0] == "-e": emul_test = 1
        
        avc_traverse(args[0])
    except:
        print("invalid command line arguments or file does not exist")
        return -1;
    return 0

if (__name__ == "__main__"):
    main()
