from fastcrud import FastCRUD

from .models import Municipio

crud_municipios: FastCRUD = FastCRUD(Municipio)
