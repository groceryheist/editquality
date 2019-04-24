<<<<<<< HEAD
#!/usr/bin/env python3

from get_labels import load_wikis, load_makefile, grep_labelfile, download_labels
=======
#!/usr/bin/env/ python3

from get_labels import load_wikis, load_makefile, grep_labelfile
>>>>>>> e0168a0bc74e27c66b9c28d0df8bd110ba58971b
from score_labels import score_labels
from move_labels_to_datalake import move_labels_to_datalake
import subprocess

wikis = load_wikis()
makefile = load_makefile()
label_files = map(lambda x: grep_labelfile(x, makefile), wikis)
download_labels(label_files)
score_labels(label_files, wikis)
<<<<<<< HEAD
move_labels_to_datalake(label_files, wikis)
subprocess.call("./get_label_user_histories.py")
subprocess.call("./evaluate_encoded_bias.py")
=======
move_labels_to_datalake(labels, wikis)
subprocess.call("evaluate_encoded_bias.py")
>>>>>>> e0168a0bc74e27c66b9c28d0df8bd110ba58971b
