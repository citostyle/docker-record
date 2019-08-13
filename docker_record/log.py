def log(message):
    filename = "debug.log"
    with open(filename, 'a') as f:
        f.write(str(message) + "\n")


