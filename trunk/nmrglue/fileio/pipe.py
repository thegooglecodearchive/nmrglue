"""
Functions for reading and writing NMRPipe binary files and table (.tab) files

NMRPipe file structure is described in the NMRPipe man pages and fdatap.h

""" 

# standard library modules
import struct 
import datetime
import os

# external modules
import numpy as np

# nmrglue modules
import fileiobase


# table reading/writing

def read_tab(file):
    """ 
    Read a NMRPipe .tab file into a records array
    """

    f = open(file)
    specials = ["VARS","FORMAT","NULLSTRING","NULLVALUE","REMARK","DATA"]
    dic = dict()
    for k in specials:
        dic[k] = []

    # first pass which finds 'special' lines 
    skiprows = 0
    for ln,line in enumerate(f):
        for k in specials:
            lk = len(k)
            if line[0:lk] == k: # the line begins with a speical string
                dic[k].append(line[lk:].lstrip().rstrip()) 
                skiprows = ln

    f.close()
    skiprows = skiprows+1   # since enumerate will start with 0

    names = dic["VARS"][0].split()  # determind the column names

    rec = np.recfromtxt(file,skiprows=skiprows,names=names)

    return dic,rec


def write_tab(filename,dic,rec,overwrite=False):
    """ 
    Write NMRPipe .tab file from a records array
    """

    f = fileiobase.open_towrite(filename,overwrite=overwrite)

    # print out the special line
    for k in dic.keys():
        if len(dic[k]) != 0:
            for line in dic[k]:
                print >> f,k,line
            print >> f,""   # extra blank line
        else:
            pass        # do nothing if no lines with special 

    
    if len(dic["FORMAT"]) != 0:
        format = dic["FORMAT"][0]
    else:
        format = "%s "*len(rec[0])

    # and print out the 
    for row in rec:
        print >> f,format % tuple(row)

    f.close()

# unit conversion functions

def make_uc(dic,data,dim=-1):
    """ 
    Make a unit conversion object
    """

    if dim == -1:
        dim = data.ndim - 1 # last dimention 

    fn = "FDF" + str(int(dic["FDDIMORDER"][data.ndim-1-dim]))
    size = float(data.shape[dim])
    
    # check for quadrature in indirect dimentions
    if (dic[fn+"QUADFLAG"] != 1) and (dim !=data.ndim-1):
        size = size/2.
        cplx = True
    else:
        cplx = False

    sw = dic[fn+"SW"]
    if sw == 0.0:   
        sw = 1.0
    obs = dic[fn+"OBS"]
    if obs == 0.0:
        obs = 1.0

    car = dic[fn+"CAR"]*obs

    return fileiobase.unit_conversion(size,cplx,sw,obs,car)


# dictionary/data creation functions

fd2dphase_dic = {"magnitude":0,"tppi":1,"states":2,"image":3}


def create_data(data):
    """ 
    Create a NMRPipe data array (recast into float32 or complex64)
    """

    if np.iscomplexobj(data):   # check quadrature
        return np.array(data,dtype="complex64")
    else:
        return np.array(data,dtype="float32")


# universal dictionary functions

def guess_udic(dic,data):
    """ 
    Guess parameter of universal dictionary from dic,data pair
    """

    # create an empty universal dictionary
    udic = fileiobase.create_blank_udic(data.ndim)

    # update default values
    for i in xrange(data.ndim):
         
        udic[i]["size"] = data.shape[i] # size from data shape
        
        # determind NMRPipe axis name
        fn = ["FDF2","FDF1","FDF3","FDF4"][(data.ndim-1)-i]
        
        # directly corresponding
        udic[i]["sw"] = dic[fn+"SW"]
        udic[i]["obs"] = dic[fn+"OBS"] 
        udic[i]["car"] = dic[fn+"CAR"]*dic[fn+"OBS"] # ppm->hz 
        udic[i]["label"] = dic[fn+"LABEL"]

        if dic[fn+"QUADFLAG"] == 1: # real data
            udic[i]["complex"] = False
        else:
            udic[i]["complex"] = True

        if dic[fn+"FTFLAG"] == 0: # time domain
            udic[i]["time"] = True
            udic[i]["freq"] = False
        else:
            udic[i]["time"] = False
            udic[i]["freq"] = True

        if i != 0:
            if  dic["FD2DPHASE"] == 0:
                udic[i]["encoding"] = "unknown" # XXX magnitude
            elif dic["FD2DPHASE"] == 1:
                udic[i]["encoding"] = "tppi"
            elif dic["FD2DPHASE"] == 2:
                udic[i]["encoding"] = "states"
            elif dic["FD2DPHASE"] == 2:
                udic[i]["encoding"] = "unknown" # XXX image
            else:
                udic[i]["encoding"] = "unknown"

    return udic


def create_dic(udic,datetimeobj=datetime.datetime.now()):
    """ 
    Crate a NMRPipe dictiony from universal dictionary
    
    Parameters:

    * udic        Universal dictionary
    * datetimeobj datetime object
    * user        Name of user
   
    Does not update dictionary keys that are unknown such as MIN/MAX,
    apodization and processing parameters, sizes in none-current domain. 
    Also rounding of parameter is different than NMRPipe.

    """

    # create the blank dictionary
    dic = create_empty_dic()    # create the empty dictionary
    dic = datetime2dic(datetimeobj,dic) # add the datetime to the dictionary

    # fill global dictionary parameters
    dic["FDDIMCOUNT"] = float(udic["ndim"])

    # fill in parameters for each dimension
    for i,adic in enumerate([udic[k] for k in xrange(udic["ndim"])]):
        n = int((dic["FDDIMCOUNT"]-1)-i)
        dic = add_axis_to_dic(dic,adic,n)

    # FD2DPHASE
    if udic[0]["encoding"] == "tppi":
        dic["FD2DPHASE"] = 1.0
    elif udic[0]["encoding"] == "states":
        dic["FD2DPHASE"] = 2.0
    else:
        dic["FD2DPHASE"] = 0.0
        
    
    if dic["FDDIMCOUNT"] >= 3: # at least 3D    
        dic["FDFILECOUNT"] = dic["FDF3SIZE"] * dic["FDF4SIZE"]

    if (dic["FDF1QUADFLAG"]==dic["FDF2QUADFLAG"]==dic["FDF3QUADFLAG"]) and (
       dic["FDF1QUADFLAG"]==dic["FDF4QUADFLAG"]==1):
        dic["FDQUADFLAG"] = 1.0


    return dic


def add_axis_to_dic(dic,adic,n):
    """ 
    Add an axis to NMRPipe dictionary

    n is 0,1,2,... (0 is direct dim, 1 first indirect...)

    """

    # determind F1,F2,F3,...
    fn = ["FDF2","FDF1","FDF3","FDF4"][n]
    
    # parameter directly in dictionary
    dic[fn+"SW"]   = float(adic["sw"])
    dic[fn+"OBS"]  = float(adic["obs"])
    dic[fn+"CAR"]  = float(adic["car"]/adic["obs"])
    dic[fn+"LABEL"] = adic["label"]

    if adic["complex"]:
        dic[fn+"QUADFLAG"]  = 0.0
    else:
        dic[fn+"QUADFLAG"]  = 1.0

    
    # determine R|I size
    if adic["complex"] and n!=0:
        psize = adic["size"]/2.
    else:
        psize = adic["size"]/1.


    # set FT/TD SIZE and FTFLAG depending on domain
    if adic["time"]:    
        dic[fn+"TDSIZE"] = psize
        dic[fn+"FTFLAG"] = 0.0
    else:
        dic[fn+"FTSIZE"] = psize
        dic[fn+"FTFLAG"] = 1.0
    
    # apodization and center
    dic[fn+"APOD"]   = dic[fn+"TDSIZE"]
    dic[fn+"CENTER"] = int(psize / 2.)+1.

    # origin (last point) is CAR*OBS-SW*(N/2-1)/N
    # see Fig 3.1 on p.36 of Hoch and Stern
    dic[fn+"ORIG"] = dic[fn+"CAR"]*dic[fn+"OBS"] - dic[fn+"SW"] * \
        (psize-dic[fn+"CENTER"])/psize
 
    if n==0:  # direct dim
        dic["FDSIZE"]     = psize
        dic["FDREALSIZE"] = psize
    
    if n==1:  # first indirect
        dic["FDSPECNUM"] = float(adic["size"]) # R+I
    
    if n==2:  # second indirect
        if adic["complex"]:
            dic["FDF3SIZE"] = psize*2
        else:
            dic["FDF3SIZE"] = psize
        
    if n==3:  # third indirect
        if adic["complex"]:
            dic["FDF4SIZE"] = psize*2
        else:
            dic["FDF3SIZE"] = psize
    return dic


def create_empty_dic():
    """ 
    Creates a nmrpipe dictionary with default values
    """

    dic =  fdata2dic(np.zeros((512),dtype="float32"))

    # parameters which are 1
    dic["FDF1CENTER"] = 1.
    dic["FDF2CENTER"] = 1.
    dic["FDF3CENTER"] = 1.
    dic["FDF4CENTER"] = 1.

    dic["FDF3SIZE"] = 1.
    dic["FDF4SIZE"] = 1.

    dic["FDF1QUADFLAG"] = 1.
    dic["FDF2QUADFLAG"] = 1.
    dic["FDF3QUADFLAG"] = 1.
    dic["FDF4QUADFLAG"] = 1.

    dic["FDSPECNUM"] = 1.
    dic["FDFILECOUNT"] = 1.
    dic["FD2DVIRGIN"] = 1.
    # dimention ordering

    dic["FDDIMORDER1"] = 2.0
    dic["FDDIMORDER2"] = 1.0
    dic["FDDIMORDER3"] = 3.0
    dic["FDDIMORDER4"] = 4.0
    dic["FDDIMORDER"] = [2.0,1.0,3.0,4.0]

    # string and such
    dic["FDF1LABEL"] = "Y"
    dic["FDF2LABEL"] = "X"
    dic["FDF3LABEL"] = "Z"
    dic["FDF4LABEL"] = "A"

    # misc values
    dic["FDFLTFORMAT"] = struct.unpack('f','\xef\xeenO')[0]
    dic["FDFLTORDER"] = 2.345

    return dic


def datetime2dic(dt,dic):
    """ 
    Add datatime object to dictionary
    """

    dic["FDYEAR"]  = float(dt.year)
    dic["FDMONTH"] = float(dt.month)
    dic["FDDAY"]   = float(dt.day)

    dic["FDHOURS"] = float(dt.hour)
    dic["FDMINS"]  = float(dt.minute)
    dic["FDSECS"]  = float(dt.second)

    return dic


def dic2datetime(dic):
    """ 
    Create a datetime object from dictionary
    """
    year   = int(dic["FDYEAR"])
    month  = int(dic["FDMONTH"])
    day    = int(dic["FDDAY"])
    hour   = int(dic["FDHOURS"])
    minute = int(dic["FDMINS"])
    second = int(dic["FDSECS"])

    return datetime.datetime(year,month,day,hour,minute,second)

# file reading

def read(filename):
    """
    Read a NMRPipe binary file returning a dic,data pair.

    For 3D/4D files filename should be a filemask with a "%" formatter.  
    """

    if "%" in filename:
        filemask = filename
        filename = filename % 1

    fdata = get_fdata(filename)
    dic = fdata2dic(fdata)  
    order = dic["FDDIMCOUNT"]
    if order == 1:
        return read_1D(filename)
    if order == 2:
        return read_2D(filename)
    if order == 3:
        return read_3D(filemask)
   
    raise ValueError,'unknown dimentionality: %s'%order


def read_lowmem(filename):
    """
    Read a NMRPipe binary file with minimal memory usage.

    For 3D/4D files filename should be a filemask with a "%" formatter.  
    """

    if "%" in filename:
        filemask = filename
        filename = filename % 1

    fdata = get_fdata(filename)
    dic = fdata2dic(fdata)  
    order = dic["FDDIMCOUNT"]
    if order == 1:
        return read_1D(filename)
    if order == 2:
        return read_2D(filename)
    if order == 3:
        return read_lowmem_3D(filemask)
   
    raise ValueError,'unknown dimentionality: %s'%order


def read_1D(filename):
    """ 
    Read a 1D NMRPipe binary file returning a dic,data pair
    """

    fdata,data = get_fdata_data(filename)   # get the fdata and data arrays
    dic = fdata2dic(fdata)  # convert the fdata block to a python dictionary
    
    data = reshape_data(data,find_shape(dic))    # reshape data
    
    # unappend imaginary data if needed
    if dic["FDF2QUADFLAG"] != 1:
        data = unappend_data(data)

    return (dic,data)


def read_2D(filename):
    """
    Read a 2D NMRPipe binary file returning a dic,data pair
    """

    fdata,data = get_fdata_data(filename)   # get the fdata and data arrays
    dic = fdata2dic(fdata)  # convert the fdata block to a python dictionary
    
    data = reshape_data(data,find_shape(dic))    # reshape data

    # unappend imaginary data if needed
    if dic["FDTRANSPOSED"] == 1 and dic["FDF1QUADFLAG"] != 1:
        data = unappend_data(data)
    elif dic["FDTRANSPOSED"] == 0 and dic["FDF2QUADFLAG"] != 1:
        data = unappend_data(data)

    return (dic,data)
        

def read_3D(filemask):
    """
    Read a 3D NMRPipe binary file returning a dic,data pair
    """

    dic,data = read_lowmem_3D(filemask)
    data = data[:,:,:]  # read all the data

    return dic,data


def read_lowmem_3D(filemask):
    """ 
    Read a NMRPipe binary file with minimal memory usage.
    """

    data = pipe_3d(filemask)    # create a new data_3d object

    dic = fdata2dic(get_fdata(data.farray[0]))

    return (dic,data)


# writing functions


def write(filename,dic,data,overwrite=False):
    """
    Write a NMRPipe file 

    For 3D files filename should be a filemask with a "%" formatter.  All
    planes are written.

    Set overwrite to True to overwrite files that exist.

    """

    order = dic["FDDIMCOUNT"]

    if order == 1:
        return write_1D(filename,dic,data,overwrite)
    if order ==2:
        return write_2D(filename,dic,data,overwrite)
    if order == 3:
        return write_3D(filename,dic,data,overwrite)
    if order == 4:
        return write_4D(filename,dic,data,overwrite)


def write_1D(filename,dic,data,overwrite=False):
    """
    Write a 1D NMRPipe file
    """

    # append imaginary and flatten
    if data.dtype=="complex64":
        data = append_data(data)
    data = unshape_data(data)
       
    # create the fdata array
    fdata = dic2fdata(dic)
    
    # write the file
    put_data(filename,fdata,data,overwrite)
    return


def write_2D(filename,dic,data,overwrite=False):
    """
    Write a 2D NMRPipe file
    """

    # append imaginary and flatten
    if data.dtype=="complex64":
        data = append_data(data)
    data = unshape_data(data)
       
    # create the fdata array
    fdata = dic2fdata(dic)
    
    # write the file
    put_data(filename,fdata,data,overwrite)
    return


def write_3D(filemask,dic,data,overwrite=False):
    """
    Write a 3D NMRPipe file
    """

    for i,plane in enumerate(data): # loop over 2D planes in data
        
        fn = filemask % (i+1)

        # update dictionary if needed
        if dic["FDSCALEFLAG"] == 1:
            dic["FDMAX"]     = plane.max()
            dic["FDDISPMAX"] = dic["FDMAX"]
            dic["FDMIN"]     = plane.min()
            dic["FDDISPMIN"] = dic["FDMIN"]

        write_2D(fn,dic,plane,overwrite)


def put_data(filename,fdata,data,overwrite=False):
    """
    Put fdata and data to 2D NMRPipe.
    """

    if data.dtype != 'float32':
        print data.dtype
        raise TypeError,'data.dtype is not float32'
    if fdata.dtype != 'float32':
        raise TypeError,'fdata.dtype is not float32'

    # write the file
    f = fileiobase.open_towrite(filename,overwrite=overwrite)
    f.write(fdata.tostring())
    f.write(data.tostring())
    f.close()
    return


def write_slice_3D(filemask,dic,data,shape,(sz,sy,sx) ):
    """ 
    Write a slice of a 3D data array to file

    Opens (or if necessary creates) 2D NMRPipe file(s) to write 
    data, where total 3D file size is given by shape.

    Parameters:
    * filemask      String with single formatting operator (%)
    * data          3D array of data
    * dic           Dictionary to write when/if files are created
    * shape         3-tuple of integers indicating the overall matrix shape
    * (sz,sy,sx)    3-tuple of slice object which specify location of data

    This function memmaps 2D NMRPipe files for speed. It only writes 
    dictionaries to file when created, leaving them unmodified if the file
    exists.  
    
    Only error checking is that data is 3D. 

    Users are not expected to use this function, rather use the iter3D object

    """
    
    if data.ndim != 3:
        raise ValueError,"passed array must be 3D"

    # unpack the shape
    dz,dy,dx = shape
    
    # create list of file names
    fnames = [filemask % i for i in range(1,dz+1)]

    # loop over the requested z-slice
    for i,f in enumerate(fnames[sz]):
    
        #print "i:",i,"f:",f

        if os.path.isfile(f) == False:
            # file doesn't exist, create a empty one        
            ndata = np.zeros( (dy,dx),dtype=data.dtype)
            write_2D(f,dic,data,False)
            del(ndata)
        
        # mmap the [new] file
        mdata = np.memmap(f,dtype='float32',offset=512*4,mode='r+')
        # reshape 
        mdata = mdata.reshape((dy,dx))
            
        # unpack into rdata,[idata] depending on quadrature
        if data.dtype == 'complex64':
            h = mdata.shape[-1]/2.0
            rdata = mdata[...,:h]
            idata = mdata[...,h:]
        else:
            rdata = mdata

        # write the data out, flush and close
        rdata[sy,sx] = data.real[i]
        rdata.flush()
        if data.dtype == 'complex64':
            idata[sy,sx] = data.imag[i]
            idata.flush()
            del(idata)

        # clean up
        del(rdata)
        del(mdata)


# iter3D tools (xyz2pipe and pipe2xyz replacements)


#Notes for iter3D implementation
#
#'x'/'y' in_lead
#==============
#Reading
#-------
#- When passed x must transposed 1,2 if dic["FDTRANSPOSED"] == 1
# (might need to call pipe_proc.tp)
#- if 'y' passed then cann pipe_proc.tp unless dic["FDTRANSPOED"]
#- save 'good' dictionary and return each loop
#
#Looping
#-------
#- will loop until data.shape[0] reached
#- returns dic, XY or YX plane
#
#Writing
#-------
#- if 'y' out then need final pipe_proc.tp of data, if 'x' do nothing
#- reshape data to 1,plane.shape[0],plane.shape[1]
#- size becomes data.shape[0],plane.shape[0],plane.shape[1]
#- sz = slice(i,i+1,1) sy=sx=slice(None)
#
#
#'z' in_lead
#===========
#Reading
#-------
#- Untranspose if dic["TRANSPOSED"] == 1 (call pipe_proc.tp)
#- transpose (1,2,0)
#- ORDER 1,2,3 = 3,1,2 and array
#- update "FDSLICECOUNT" and "FDSIZE" taking into accound complex packing
#- also update "FDSPECNUM"
#- call write_slice3D
#- store shape as self.max_iter
#
#Looping
#-------
#- grab the slice and pack_complex if needed
#- returns dic,ZX-plane
#
#Writing
#-------
#- if out_lead = 'x' needs final pipe_proc.tp of data, if 'z' do nothing
#- reshape data to 1,plane.shape[0],plane.shape[1]
#- transposed data to 2,0,1 (or combine with above step
#- update "FDSIZE" and "FDSPECNUM"
#- remove min/max
#- update FDDIMORDER and ORDER1,2,3
#- size plane.shape[0],self.max_iter,plane.shape[2]
#- sz = slice(None)=sx
#- sy = slice(i,i+1,1)


def pack_complex(data):
    """
    Pack inteleaved real,imag array into complex array
    """
    return np.array(data[...,::2]+data[...,1::2]*1.j,dtype="complex64")


def transpose_3D(dic,data,(a1,a2,a3)=(2,1,0) ):
    """ 
    Transpose pipe_3d object and dictionary
    """

    rdic = dict(dic)    # create a copy of the dictionary
    
    # transpose the data
    data = data.transpose( (a1,a2,a3) )

    # transpose the dictionary
    s3 = "FDDIMORDER"+str(int(3-a1))    # 3rd axis is 0th axis in data_3d
    s2 = "FDDIMORDER"+str(int(3-a2))    # 2nd axis is 1st axis in data_3d
    s1 = "FDDIMORDER"+str(int(3-a3))    # 1st axis is 3nd axis in data_3d

    rdic["FDDIMORDER1"] = dic[s1]
    rdic["FDDIMORDER2"] = dic[s2]
    rdic["FDDIMORDER3"] = dic[s3]

    rdic['FDDIMORDER'] = [ rdic["FDDIMORDER1"], rdic["FDDIMORDER2"],
                           rdic["FDDIMORDER3"], rdic["FDDIMORDER4"] ]

    # set the shape dictionary parameters
    fn = "FDF"+str(int(rdic["FDDIMORDER1"]))
    if rdic[fn+"QUADFLAG"] != 1.0:   # last axis is complex
        rdic["FDSIZE"] = data.shape[2]/2.
    else:   # last axis is singular
        rdic["FDSIZE"] = data.shape[2]

    rdic["FDSLICECOUNT"] = data.shape[1]
    rdic["FDSPECNUM"] = rdic["FDSLICECOUNT"]

    return rdic,data


class iter3D(object):
    """ 
    Object which allows for graceful iteration over 3D NMRPipe files

    iter3D.iter() returns a (dic,plane) tuple which can be written using
    the x.writeplane function.

    When processing 3D files with iter3D object(s) the following dictionary 
    parameters may not have the same values as NMRPipe processing scripts 
    return:

    FDSLICECOUNT and
    
    FDMAX,FDDISMAX,FDMIN,FDDISPMIN when FDSCALEFLAG == 0

    Example:

    #3D data processing:
    xiter = iter3D("data/test%03d.fid","x","x")
    for dic,YXplane in xiter:
        # process X and Y axis
        xiter.write("ft/test%03d.ft2",YXplane,dic)
    
    ziter = iter3D("ft/test%03d.ft2","z","z")
    for dic,XZplane in ziter:
        # process Z axis
        ziter.write("ft/test%03d.ft3",XZplane,dic)

    """

    def __init__(self,filemask,in_lead="x",out_lead="DEFAULT"):
        """
        Create a iter3D object

        Parameters:
        * filemask  string with single formatter (%) of NMRPipe files to read
        * in_lead   Axis name ('x','y','z') of last (1st) axis in outputed 2D 
        * out_lead  Axis name ('x','y','z') of axis to be written typically
                    this is the same as in_lead

        =======     ===============
        In-lead     Iterated Planes
        =======     ===============
        "x"         ('y','x')
        "y"         ('x','y')
        "z"         ('x','z') 
        =======     ===============

        """

        # check for invalid in_lead, out_lead
        if in_lead not in ["x","y","z"]:
            raise ValueError,"in_lead must be 'x','y' or 'z'"

        if out_lead not in ["x","y","z","DEFAULT"]:
            raise ValueError,"out_lead must be 'x','y','z' or 'DEFAULT'"

        if out_lead == "DEFAULT":
            out_lead = in_lead

        if in_lead in ["x","y"] and out_lead not in ["x","y"]:
            raise ValueError,"Invalid in_lead, out_lead pair"

        if in_lead == "z" and out_lead not in ["x","z"]:
            raise ValueError,"Invalid in_lead, out_lead pair"

        self.in_lead  = in_lead
        self.out_lead = out_lead

        self.dic,self.pipe_3d = read_3D(filemask)
  
        # uptranspose data if needed
        if self.dic["FDTRANSPOSED"] == 1.0:
            # need to switch X and Y (0,2,1)
            self.dic,self.pipe_3d = transpose_3D(self.dic,self.pipe_3d,(0,2,1))

        # self.pipe_3d and self.dic are now REALLY ZYX order
       
        # now prep pipe_3d for slicing and be make
        # idic the iterator dictionary

        self.i = -1  # counter

        if self.in_lead == "x":
            # leave as is Z(YX)
            self.needs_pack_complex = False
            self.idic = dict(self.dic)
            self.i_max = int(self.pipe_3d.shape[0])

        elif self.in_lead == "y":
            # transpose to Z(XY)
            self.idic,self.pipe_3d = transpose_3D(self.dic,self.pipe_3d,(0,2,1))
            self.needs_pack_complex = False
            self.i_max = int(self.pipe_3d.shape[0])

        elif self.in_lead == "z":
            # transpose to Y(XZ)
            self.idic,self.pipe_3d = transpose_3D(self.dic,self.pipe_3d,(1,2,0))
            fn = "FDF"+str(int(self.idic["FDDIMORDER1"]))
            if self.idic[fn+"QUADFLAG"] != 1.0:   # z axis is complex
                self.needs_pack_complex = True
            else:
                self.needs_pack_complex = False
            self.i_max = int(self.pipe_3d.shape[0])
        else:
            raise Error,"You should NEVER get here"


    def __iter__(self):
        """ 
        x.__iter__() <==> iter(x)
        """
        return self

    def next(self):
        """ 
        Return the next dic,plane or raise StopIteration
        """
        self.i = self.i + 1
        if self.i >= self.i_max:
            raise StopIteration
        else:
            plane = self.pipe_3d[self.i]
            if self.needs_pack_complex:
                plane = pack_complex(plane)
            return (dict(self.idic),plane)

    def reinitialize(self):
        """ 
        Restart iterator at first dic,plane
        """
        self.i = -1


    def write(self,filemask,plane,dic):
        """ 
        Write out current plane
        """

        # make the plane a 3D array
        plane = plane.reshape(1,plane.shape[0],plane.shape[1])

        if self.in_lead != self.out_lead:
            # transpose the last two axes
            dic,plane = transpose_3D(dic,plane,(0,2,1))
            

        if self.in_lead == "x" or self.in_lead=="y":
            shape = ( self.i_max,plane.shape[1],plane.shape[2] )
            sz = slice(self.i,self.i+1,1)
            sx = slice(None)
            sy = slice(None)

        elif self.in_lead == "z":
            # reorder from YXZ -> ZYX
            dic,plane = transpose_3D(dic,plane,(2,0,1))
            
            # turn scale flag off
            dic["FDSCALEFLAG"] = 0.0
            # the Y size is incorrect
            dic["FDSPECNUM"] = self.i_max

            # update the file count XXX these should be done bettwe
            dic["FDFILECOUNT"] = plane.shape[0]
            dic["FDF3SIZE"] = plane.shape[0]

            shape = ( plane.shape[0],self.i_max,plane.shape[2] )
            sx = slice(None)
            sy = slice(self.i,self.i+1,1)
            sz = slice(None)

        else:
            raise Error,"You should NEVER get here"

        #print "Writing out slice :",self.i
        #print "shape:",shape
        #print "plane.shape",plane.shape
        #print "sx,sy,sz",sx,sy,sz
        #print dic["FDFILECOUNT"]
        write_slice_3D(filemask,dic,plane,shape,(sz,sy,sx) )


# Shaping functions

def find_shape(dic):
    """ 
    Find the shape (tuple) of data in a NMRPipe file from dictionary
    """

    if dic["FDDIMCOUNT"] == 1: # 1D Data

        if dic["FDF2QUADFLAG"] == 1:
            multi = 1.0
        else:
            multi = 2.0

        dim1 = int(dic["FDSIZE"]*multi)
        return (dim1)

    else: # 2D+ Data
        
        if dic["FDF1QUADFLAG"] == 1 and dic["FDTRANSPOSED"] == 1:
            multi = 1.0
        elif dic["FDF2QUADFLAG"] == 1 and dic["FDTRANSPOSED"] == 0:
            multi = 1.0
        else:
            multi = 2.0

        dim1 = int(dic["FDSIZE"]*multi)
        dim2 = dic["FDSPECNUM"]

        # when the direct dim is singular and the indirect 
        # dim is complex FDSPECNUM is half of the correct value
        if dic["FDQUADFLAG"] == 0 and multi == 1.0:
            dim2 = dim2*2

        return (dim2,dim1)


def reshape_data(data,shape):
    """ 
    Reshape data or return 1D data after warning
    """
    try:
        return data.reshape(shape)
    except ValueError:
            print "Warning:",data.shape,"cannot be shaped into",shape
            return data


def unshape_data(data):
    """ 
    Returns 1D version of data
    """
    return data.flatten()


def unappend_data(data):
    """ 
    Returns complex data with last axis (-1) unappended

    Data should have imaginary data vector appended to real data vector

    """
    h = data.shape[-1]/2.0
    return np.array(data[...,:h]+data[...,h:]*1.j,dtype="complex64")


def append_data(data):
    """ Return data with last axis (-1) appeneded

    Data should be complex

    """
    return np.concatenate( (data.real,data.imag) , axis=-1)


# fdata functions

def fdata2dic(fdata):
    """ 
    Convert a fdata array to fdata dictionary
    
    Converts the raw 512x4-byte NMRPipe header into a python dictionary
    with keys as given in fdatap.h
    """

    dic = dict()

    # Populate the dictionary with FDATA which contains numbers
    for key in fdata_dic.keys():
        dic[key] = float(fdata[ int( fdata_dic[key] ) ])
		
    # make the FDDIMORDER
    dic["FDDIMORDER"] = [dic["FDDIMORDER1"],dic["FDDIMORDER2"],  \
                         dic["FDDIMORDER3"],dic["FDDIMORDER4"]]
	
    # Populate the dictionary with FDATA which contains strings
    dic["FDF2LABEL"] = struct.unpack('8s',fdata[16:18])[0].rstrip('\x00')
    dic["FDF1LABEL"] = struct.unpack('8s',fdata[18:20])[0].rstrip('\x00')
    dic["FDF3LABEL"] = struct.unpack('8s',fdata[20:22])[0].rstrip('\x00')
    dic["FDF4LABEL"] = struct.unpack('8s',fdata[22:24])[0].rstrip('\x00')
    dic["FDSRCNAME"]  = struct.unpack('16s' ,fdata[286:290])[0].rstrip('\x00')
    dic["FDUSERNAME"] = struct.unpack('16s' ,fdata[290:294])[0].rstrip('\x00')
    dic["FDTITLE"]    = struct.unpack('60s' ,fdata[297:312])[0].rstrip('\x00')
    dic["FDCOMMENT"]  = struct.unpack('160s',fdata[312:352])[0].rstrip('\x00')
    dic["FDOPERNAME"] = struct.unpack('32s' ,fdata[464:472])[0].rstrip('\x00')

    return dic


def dic2fdata(dic):
    """ 
    Converts a NMRPipe dictionary into an array
    """

    # A 512 4-byte array to hold the nmrPipe header data
    fdata = np.zeros(512,'float32')

    # Populate the array with the simple numbers
    for key in fdata_nums.keys():
        fdata[ int( fdata_dic[key])] = float(dic[key])

    # Check that FDDIMORDER didn't overwrite FDDIMORDER1
    fdata[ int(fdata_dic["FDDIMORDER1"]) ] = dic["FDDIMORDER1"] 

    # Pack the various strings into terminated strings of the correct length
    # then into floats in the fdata array
    fdata[16:18] = struct.unpack('2f', struct.pack('8s',dic["FDF2LABEL"]) )
    fdata[18:20] = struct.unpack('2f', struct.pack('8s',dic["FDF1LABEL"]) )
    fdata[20:22] = struct.unpack('2f', struct.pack('8s',dic["FDF3LABEL"]) )
    fdata[22:24] = struct.unpack('2f', struct.pack('8s',dic["FDF4LABEL"]) )

    # and the longer strings (typically blank)
    fdata[286:290]=struct.unpack( '4f', struct.pack( '16s',dic["FDSRCNAME"]))
    fdata[290:294]=struct.unpack( '4f', struct.pack( '16s',dic["FDUSERNAME"]))
    fdata[297:312]=struct.unpack('15f', struct.pack( '60s',dic["FDTITLE"]))
    fdata[312:352]=struct.unpack('40f', struct.pack('160s',dic["FDCOMMENT"]))	
    fdata[464:472]=struct.unpack( '8f', struct.pack( '32s',dic["FDOPERNAME"]))

    return fdata


# Raw Reading of Data from file

def get_fdata(filename):
    """
    Get an array of length 512 holding NMRPipe header
    """
    fdata =  np.fromfile(filename,'float32',512)

    if fdata[2] - 2.345 > 1e-6:    # fdata[2] should be 2.345
        fdata = fdata.byteswap()
    
    return fdata


def get_data(filename):
    """
    Get array of data
    """

    data = np.fromfile(filename,'float32')

    if data[2] - 2.345 > 1e-6:  # check for byteswap
        data = data.byteswap()

	return data[512:]


def get_fdata_data(filename):
    """ 
    Get fdata and data array, returns (fdata,data)
    """
    data = np.fromfile(filename,'float32')
    if data[2] - 2.345 > 1e-6:  # check for byteswap
        data = data.byteswap()

    return data[:512],data[512:]


# pipe_3d objects and related functions


def flist_from_filemask(filemask):
    """ 
    Return list of files that match filemask
    """
    # split into directory and fm
    d,fm = os.path.split(filemask)
    if d == '':
        d = '.'

    flist = []
    i = 1
    while fm % i in os.listdir(d):
        flist.append(os.path.join(d,fm%i))
        i = i+1

    return flist


class pipe_3d(fileiobase.data_3d):
    """ 
    pipe_3d emulates numpy.ndarray objects without loading data into memory

    * slicing operations return ndarray objects.
    * can iterate over with expected results.
    * transpose and swapaxes functions create a new fid_2d object with the
      new axes ordering.
    * has ndim, shape, and dtype attributes.
    
    """

    # basic method objects

    def __init__(self,filemask,order = ["z","y","x"]):    
        """
        Create and set up object
        """

        self.filemask = filemask
        self.farray = flist_from_filemask(filemask)
        
        if len(self.farray) == 0:
            raise IOError,"no file match filemask %s"%filemask

        dic,data = read_2D(self.farray[0]) # read in the first 2D plane

        if len(self.farray) != dic["FDFILECOUNT"]:

            if len(self.farray) >  dic["FDFILECOUNT"]:
                print "Warning: more file match filemask than indicated fdata"
                #print len(self.farray),dic["FDFILECOUNT"]
                self.farray = self.farray[:int(dic["FDFILECOUNT"])]
            else:
                raise IOError,"Incomplete 3D file"

        self.lenX = int(data.shape[1])
        self.lenY = int(data.shape[0])
        self.lenZ = len(self.farray)

        self.order = order

        a =  [self.lenZ,self.lenY,self.lenX]
        self.shape = (a[order.index("z")],a[order.index("y")],
                      a[order.index("x")] )

        self.dtype = data.dtype
        self.ndim = 3

        # clean up 
        del(dic)
        del(data)


    def __fcopy__(self,order):
        """ 
        Create a copy 
        """

        n = pipe_3d(self.filemask,order)
        return n


    def __fgetitem__(self, (sZ,sY,sX) ):
        """ 
        Return ndarray of selected values

        (sz,sy,sx) is a well formated tuple of slices

        """
        
        # make an empty data array
        lensZ = len(range(self.lenZ)[sZ])
        lensY = len(range(self.lenY)[sY])
        lensX = len(range(self.lenX)[sX])

        out = np.empty( (lensZ,lensY,lensX) , dtype=self.dtype)

        #read in the data
        for jZ,iZ in enumerate(range(self.lenZ)[sZ]):
            fdic,data = read_2D(self.farray[iZ])
            data = data[(sY,sX)]
            out[jZ] = data

        return out

# data, see fdata.h

fdata_nums = {
	'FDF4CENTER': '82', 'FDF2P0': '109', 'FDF2P1': '110', 'FDF1P1': '246',
	'FDF2X1': '257', 'FDF1P0': '245', 'FDF3AQSIGN': '476', 'FDDISPMAX': '251',
	'FDF4FTFLAG': '31', 'FDF3X1': '261', 'FDRANK': '180', 'FDF2C1': '418',
	'FDF2QUADFLAG': '56', 'FDSLICECOUNT': '443', 'FDFILECOUNT': '442',
	'FDMIN': '248', 'FDF3OBS': '10', 'FDF4APODQ2': '407', 'FDF4APODQ1': '406', 
	'FDF3FTSIZE': '200', 'FDF1LB': '243', 'FDF4C1': '409', 'FDF4QUADFLAG': '54',
	'FDF1SW': '229', 'FDTRANSPOSED': '221', 'FDSECS': '285', 'FDF1APOD': '428',
	'FDF2APODCODE': '413', 'FDPIPECOUNT': '75',
	'FDPEAKBLOCK': '362', 'FDREALSIZE': '97', 'FDF4SIZE': '32',
	'FDF4SW': '29', 'FDF4ORIG': '30', 'FDF3XN': '262', 'FDF1OBS': '218',
	'FDDISPMIN': '252', 'FDF2XN': '258', 'FDF3P1': '61', 'FDF3P0': '60',
	'FDF1ORIG': '249', 'FDF2FTFLAG': '220', 'FDF1TDSIZE': '387', 'FDLASTPLANE': '78',
	'FDF1ZF': '437', 'FDF4FTSIZE': '201', 'FDF3C1': '404', 'FDFLTFORMAT': '1',
	'FDF4CAR': '69', 'FDF1FTFLAG': '222', 'FDF2OFFPPM': '480',
	'FDSIZE': '99', 'FDYEAR': '296', 'FDF1C1': '423', 'FDUSER3': '72',
	'FDF1FTSIZE': '98', 'FDMINS': '284', 'FDSCALEFLAG': '250', 'FDF3TDSIZE': '388',
	'FDPARTITION': '65', 'FDF3FTFLAG': '13', 'FDF2APODQ1': '415',
	'FD2DVIRGIN': '399', 'FDF2APODQ3': '417', 'FDF2APODQ2': '416',
	'FD2DPHASE': '256', 'FDMAX': '247', 'FDF3SW': '11', 'FDF4TDSIZE': '389',
	'FDPIPEFLAG': '57', 'FDDAY': '295', 'FDF2UNITS': '152', 'FDF4APODQ3': '408',
	'FDFIRSTPLANE': '77', 'FDF3SIZE': '15', 'FDF3ZF': '438',
	'FDF3ORIG': '12', 'FD1DBLOCK': '365', 'FDF1AQSIGN': '475', 'FDF2OBS': '119',
	'FDF1XN': '260', 'FDF4UNITS': '59', 'FDDIMCOUNT': '9', 'FDF4XN': '264',
	'FDUSER2': '71', 'FDF4APODCODE': '405', 'FDUSER1': '70', 'FDMCFLAG': '135',
	'FDFLTORDER': '2', 'FDUSER5': '74', 'FDF3QUADFLAG': '51',
	'FDUSER4': '73', 'FDTEMPERATURE': '157', 'FDF2APOD': '95', 'FDMONTH': '294',
	'FDF4OFFPPM': '483', 'FDF3OFFPPM': '482', 'FDF3CAR': '68', 'FDF4P0': '62', 
	'FDF4P1': '63', 'FDF1OFFPPM': '481', 'FDF4APOD': '53', 'FDF4X1': '263',
	'FDLASTBLOCK': '359', 'FDPLANELOC': '14', 'FDF2FTSIZE': '96',
	'FDF1X1': '259', 'FDF3CENTER': '81', 'FDF1CAR': '67', 'FDMAGIC': '0', 
	'FDF2ORIG': '101', 'FDSPECNUM': '219', 'FDF2AQSIGN': '64',
	'FDF1UNITS': '234', 'FDF2LB': '111', 'FDF4AQSIGN': '477', 'FDF4ZF': '439',
	'FDTAU': '199', 'FDNOISE': '153', 'FDF3APOD': '50',
	'FDF1APODCODE': '414', 'FDF2SW': '100', 'FDF4OBS': '28', 'FDQUADFLAG': '106',
	'FDF2TDSIZE': '386', 'FDHISTBLOCK': '364', 
	'FDBASEBLOCK': '361', 'FDF1APODQ2': '421', 'FDF1APODQ3': '422',
	'FDF1APODQ1': '420', 'FDF1QUADFLAG': '55', 'FDF3UNITS': '58', 'FDF2ZF': '108',
	'FDCONTBLOCK': '360', 'FDDIMORDER4': '27', 'FDDIMORDER3': '26', 
	'FDDIMORDER2': '25', 'FDDIMORDER1': '24', 'FDF2CAR': '66', 'FDF3APODCODE': '400',
	'FDHOURS': '283', 'FDF1CENTER': '80', 'FDF3APODQ1': '401', 'FDF3APODQ2': '402',
	'FDF3APODQ3': '403', 'FDBMAPBLOCK': '363', 'FDF2CENTER': '79'}

fdata_dic = {
	'FDF4CENTER': '82', 'FDF2P0': '109', 'FDF2P1': '110', 'FDF1P1': '246',
	'FDF2X1': '257', 'FDF1P0': '245', 'FDF3AQSIGN': '476', 'FDDISPMAX': '251',
	'FDF4FTFLAG': '31', 'FDF3X1': '261', 'FDRANK': '180', 'FDF2C1': '418',
	'FDF2QUADFLAG': '56', 'FDSLICECOUNT': '443', 'FDFILECOUNT': '442',
	'FDMIN': '248', 'FDF3OBS': '10', 'FDF4APODQ2': '407', 'FDF4APODQ1': '406', 
	'FDF3FTSIZE': '200', 'FDF1LB': '243', 'FDF4C1': '409', 'FDF4QUADFLAG': '54',
	'FDF1SW': '229', 'FDTRANSPOSED': '221', 'FDSECS': '285', 'FDF1APOD': '428',
	'FDF2APODCODE': '413', 'FDPIPECOUNT': '75', 'FDOPERNAME': '464',
	'FDF3LABEL': '20', 'FDPEAKBLOCK': '362', 'FDREALSIZE': '97', 'FDF4SIZE': '32',
	'FDF4SW': '29', 'FDF4ORIG': '30', 'FDF3XN': '262', 'FDF1OBS': '218',
	'FDDISPMIN': '252', 'FDF2XN': '258', 'FDF3P1': '61', 'FDF3P0': '60',
	'FDF1ORIG': '249', 'FDF2FTFLAG': '220', 'FDF1TDSIZE': '387', 'FDLASTPLANE': '78',
	'FDF1ZF': '437', 'FDF4FTSIZE': '201', 'FDF3C1': '404', 'FDFLTFORMAT': '1',
	'FDF4CAR': '69', 'FDF1FTFLAG': '222', 'FDF2OFFPPM': '480', 'FDF1LABEL': '18',
	'FDSIZE': '99', 'FDYEAR': '296', 'FDF1C1': '423', 'FDUSER3': '72',
	'FDF1FTSIZE': '98', 'FDMINS': '284', 'FDSCALEFLAG': '250', 'FDF3TDSIZE': '388',
	'FDTITLE': '297', 'FDPARTITION': '65', 'FDF3FTFLAG': '13', 'FDF2APODQ1': '415',
	'FD2DVIRGIN': '399', 'FDF2APODQ3': '417', 'FDF2APODQ2': '416',
	'FD2DPHASE': '256', 'FDMAX': '247', 'FDF3SW': '11', 'FDF4TDSIZE': '389',
	'FDPIPEFLAG': '57', 'FDDAY': '295', 'FDF2UNITS': '152', 'FDF4APODQ3': '408',
	'FDFIRSTPLANE': '77', 'FDF3SIZE': '15', 'FDF3ZF': '438', 'FDDIMORDER': '24',
	'FDF3ORIG': '12', 'FD1DBLOCK': '365', 'FDF1AQSIGN': '475', 'FDF2OBS': '119',
	'FDF1XN': '260', 'FDF4UNITS': '59', 'FDDIMCOUNT': '9', 'FDF4XN': '264',
	'FDUSER2': '71', 'FDF4APODCODE': '405', 'FDUSER1': '70', 'FDMCFLAG': '135',
	'FDFLTORDER': '2', 'FDUSER5': '74', 'FDCOMMENT': '312', 'FDF3QUADFLAG': '51',
	'FDUSER4': '73', 'FDTEMPERATURE': '157', 'FDF2APOD': '95', 'FDMONTH': '294',
	'FDF4OFFPPM': '483', 'FDF3OFFPPM': '482', 'FDF3CAR': '68', 'FDF4P0': '62', 
	'FDF4P1': '63', 'FDF1OFFPPM': '481', 'FDF4APOD': '53', 'FDF4X1': '263',
	'FDLASTBLOCK': '359', 'FDPLANELOC': '14', 'FDF2FTSIZE': '96', 'FDUSERNAME': '290',
	'FDF1X1': '259', 'FDF3CENTER': '81', 'FDF1CAR': '67', 'FDMAGIC': '0', 
	'FDF2ORIG': '101', 'FDSPECNUM': '219', 'FDF2LABEL': '16', 'FDF2AQSIGN': '64',
	'FDF1UNITS': '234', 'FDF2LB': '111', 'FDF4AQSIGN': '477', 'FDF4ZF': '439',
	'FDTAU': '199', 'FDF4LABEL': '22', 'FDNOISE': '153', 'FDF3APOD': '50',
	'FDF1APODCODE': '414', 'FDF2SW': '100', 'FDF4OBS': '28', 'FDQUADFLAG': '106',
	'FDF2TDSIZE': '386', 'FDHISTBLOCK': '364', 'FDSRCNAME': '286', 
	'FDBASEBLOCK': '361', 'FDF1APODQ2': '421', 'FDF1APODQ3': '422',
	'FDF1APODQ1': '420', 'FDF1QUADFLAG': '55', 'FDF3UNITS': '58', 'FDF2ZF': '108',
	'FDCONTBLOCK': '360', 'FDDIMORDER4': '27', 'FDDIMORDER3': '26', 
	'FDDIMORDER2': '25', 'FDDIMORDER1': '24', 'FDF2CAR': '66', 'FDF3APODCODE': '400',
	'FDHOURS': '283', 'FDF1CENTER': '80', 'FDF3APODQ1': '401', 'FDF3APODQ2': '402',
	'FDF3APODQ3': '403', 'FDBMAPBLOCK': '363', 'FDF2CENTER': '79'}