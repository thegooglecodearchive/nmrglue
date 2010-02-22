#! /usr/bin/env python

import nmrglue as ng

# read in the file
dic,data = ng.pipe.read("../common_data/1d_pipe/test.fid")

# process the direct dimension
dic,data = ng.pipe_proc.sp(dic,data,off=0.35,end=0.98,pow=2,c=1.0)
dic,data = ng.pipe_proc.zf(dic,data,auto=True)
dic,data = ng.pipe_proc.ft(dic,data,auto=True)
dic,data = ng.pipe_proc.ps(dic,data,p0=-17.7,p1=-36.0)
dic,data = ng.pipe_proc.di(dic,data)

# write out processed data
ng.pipe.write("1d_pipe.ft",dic,data,overwrite=True)

# check against a file processed with NMRPipe
dic1,data1 = ng.pipe.read("../common_data/1d_pipe/test.ft")
dic2,data2 = ng.pipe.read("1d_pipe.ft")
print ng.misc.pair_similar(dic1,data1,dic2,data2,verb=True)
