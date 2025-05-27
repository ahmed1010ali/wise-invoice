

import os
import re
import io
import cv2
import json
import yaml
import tempfile
import numpy as np
import pandas as pd
from PIL import Image
import arabic_reshaper
from uuid import uuid4
from crewai.llm import LLM
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from datetime import timedelta
from langchain.tools import tool
from reportlab.lib import colors
from sklearn.cluster import KMeans
from HelperFunctions.Tools import *
from rapidfuzz import process, fuzz
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER
from langchain.schema import SystemMessage
from supabase import create_client, Client
from fastapi.staticfiles import StaticFiles
from marker.models import create_model_dict
from reportlab.pdfbase.ttfonts import TTFont
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse
from sklearn.preprocessing import StandardScaler
from marker.converters.table import TableConverter
from langchain.agents.agent_types import AgentType
from langchain.agents import initialize_agent, Tool
from reportlab.lib.styles import getSampleStyleSheet
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from pdf2image import convert_from_bytes, convert_from_path
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer











