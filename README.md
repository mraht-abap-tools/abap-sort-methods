# Sort ABAP methods by alphabet

## Prerequisites:
* https://www.python.org/downloads/

## Step by step:
1. Use python to start the program
2. Input the path to a text file containing the source code of the class
3. Confirm your input with ENTER

The program generates a new text file '<filename>_sorted.<extension>' which contains the sorted source code.
The original file is only being read and not being written in any case!

## Notes:
Method definitions are being sorted by visibility section and name.
Method implementations are being sorted by name only.
For an example please see 'lcl_test.abap'.
