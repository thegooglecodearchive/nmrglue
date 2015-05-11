Information on nmrglue is also avialable on the main nmrglue webpage, http://nmrglue.com.

## What is nmrglue? ##

Nmrglue is a module for working with NMR data in Python. When used with the [NumPy](http://numpy.scipy.org), [SciPy](http://scipy.org), and [matplotlib](http://matplotlib.sourceforge.net/index.html) packages nmrglue provides a robust environment for rapidly developing new methods for processing, analyzing, and visualizing NMR data.  Nmrglue also provides a framework for connecting existing NMR software packages.

## What can nmrglue do? ##

Nmrglue has the ability to read, write and convert between a number of common NMR file formats including Agilent/Varian, Bruker, NMRPipe, Sparky SIMPSON, and Rowland NMR Toolkit files. The files, which are represented in Python as dictionaries of spectral parameters and [NumPy](http://numpy.scipy.org) ndarray objects, can be easily examined, modified and processed as desired.

Nmrglue provides a number of functions for processing NMR data such as apodization, spectral shifting, Fourier and other transformations, baseline smoothing and flattening, and linear prediction modeling and extrapolation. In addition new processing schemes can be implemented easily using the nmrglue provided functions and the multitude of numerical routines provided by the [NumPy](http://numpy.scipy.org) and [SciPy](http://scipy.org) packages.

When used in conjunction with the [matplotlib](http://matplotlib.sourceforge.net/index.html) (or other) python plotting library nmrglue can be used to create publication quality figures of NMR spectrum or examine data interactively.  For example:

<img src='http://nmrglue.com/images/spectrum_2d.png' width='400' height='300'>
<img src='http://nmrglue.com/images/strip_plots.png' height='300'>

nmrglue can be used to analysis NMR data, with routines to perform peak picking, multidimensional lineshape fitting (peak fitting), and peak integration provided within the package. New analysis methods can be rapidly developed and tested in Python or by integrating Fortran and C/C++ code.<br>
<br>
<h2>Installation</h2>

Nmrglue requires the following packages<br>
<br>
<ul><li><a href='http://numpy.scipy.org'>NumPy</a>
</li><li><a href='http://scipy.org'>SciPy</a></li></ul>

and the following are recommended (especially if you wish to run the examples):<br>
<br>
<ul><li><a href='http://matplotlib.sourceforge.net/index.html'>matplotlib</a>
</li><li><a href='http://ipython.scipy.org/moin/'>IPython</a></li></ul>

To install nmrglue on windows download and run the Windows binary (.exe).  On Linux and OS X download the tar.gz file, extract, and run:<br>
<br>
<blockquote>$ python setup.py install</blockquote>

Additional detail on installing nmrglue can be found in the <a href='http://jjhelmus.github.com/nmrglue/current/install.html'>Install Guide</a>.<br>
<br>
<br>
<h2>Documentation</h2>

Documentation for nmrglue can be found in the online <a href='http://jjhelmus.github.com/nmrglue/current/index.html'>documentation</a> or using Python's built in help system. New users of the package can use the <a href='http://jjhelmus.github.com/nmrglue/current/tutorial.html'>nmrglue tutorial</a> to learn about many useful features.  A number of <a href='http://jjhelmus.github.com/nmrglue/current/examples/index.html'>examples</a> are also provided for those wishing to see nmrglue is action.  The <a href='http://jjhelmus.github.com/nmrglue/current/reference/index.html'>reference guide</a> may be of use to those needing a detailed information about the functions and classes in nmrglue. There is also a <a href='https://github.com/jjhelmus/nmrglue/wiki'>Wiki</a> for user contributed hints and code snippets. A <a href='http://www.youtube.com/watch?v=pTxJFvLhHhI'>video</a> describing nmrglue is also available from the talk given by Jonathan Helmus at the 2012 Scientific Python conference.<br>
<br>
There is also an <a href='http://link.springer.com/article/10.1007%2Fs10858-013-9718-x'>article</a> in the Journal of Biomolecular NMR on nmrglue. The examples from this article are <a href='http://jjhelmus.github.com/nmrglue/current/jbnmr_examples/index.html'>available</a> online along with <a href='http://code.google.com/p/nmrglue/downloads/list?q=label:Article-Examples'>corresponding data</a>.<br>
<br>
<br>
<h2>Citing nmrglue</h2>

The article describing nmrglue has been published in the Journal of Biomolecular NMR.  Please use the following citation if you find nmrglue useful in your research:<br>
<br>
J.J. Helmus, C.P. Jaroniec, Nmrglue: An open source Python package for the analysis of multidimensional NMR data, J. Biomol. NMR 2013, 55, 355-367. <a href='http://dx.doi.org/10.1007/s10858-013-9718-x'>10.1007/s10858-013-9718-x</a>.<br>
<br>
<h2>Getting help</h2>

nmrglue has a <a href='http://groups.google.com/group/nmrglue-discuss'>mailing list</a> which you can ask question on and request help.  Also feel free to email the <a href='http://nmrglue.com/jhelmus'>creator of nmrglue, Jonathan Helmus</a> directly. If you want to receive emails when a new version of nmrglue is released subscribe to the <a href='http://groups.google.com/group/nmrglue-announce'>nmrglue-announce</a> group.<br>
<br>
<h2>Contributing</h2>

Nmrglue is an open source software package distributed under the <a href='http://opensource.org/licenses/BSD-3-Clause'>New BSD License</a>. Source code for the package is available on <a href='http://github.com/jjhelmus/nmrglue'>GitHub</a>. Feature requests and bug reports can be sumbitted to the <a href='https://github.com/jjhelmus/nmrglue/issues'>issue tracker</a>, posting to the <a href='http://groups.google.com/group/nmrglue-discuss'>nmrglue mailing list</a> or contacting Jonathan Helmus directly. Contributions of source code or example are always appreciated from both developers and users.