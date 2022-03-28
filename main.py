import os

dirname = 'chinese/lesson1/'
files = os.listdir(dirname)
dirname2 = 'chinese/lesson1/start_image'
files2 = os.listdir(dirname2)
for file in files:
    if os.path.isdir(os.path.join(dirname, file)):
        continue
    print(os.path.join(dirname, file))
print(os.path.join(dirname, files2[0]))