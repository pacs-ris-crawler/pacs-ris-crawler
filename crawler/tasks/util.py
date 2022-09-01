from flask import current_app


def load_config():
    return current_app.config


def load_dicom_config(dicom_node):
    return current_app.config["DICOM_NODES"][dicom_node]

def dict_to_str(parameter_dict):
    return "".join(["{}_{}".format(k, v) for k, v in parameter_dict.items()])
