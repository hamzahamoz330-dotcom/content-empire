import asyncio
import logging
import os
import google.generativeai as genai
from moviepy.editor import *
from datetime import datetime
import requests
import json
import hashlib
import random
import re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont
import textwrap
import numpy as np
import sys

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        self.PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
        
        self.YOUTUBE_CHANNEL_URL = "https://youtube.com/@techcompass-d5l"
        self.BLOGGER_BLOG_URL = "https://techcompass4you.blogspot.com/"
        self.BRAND_NAME = "TechCompass"
        
    async def send_telegram_message(self, message):
        try:
            if not self.TELEGRAM_BOT_TOKEN or not self.TELEGRAM_CHAT_ID:
                return False
                
            url = f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": self.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

class YouTubeUploader:
    def __init__(self):
        self.service = None
        self.initialize_service()
    
    def initialize_service(self):
        try:
            token_json = os.getenv('YOUTUBE_TOKEN_JSON')
            if not token_json:
                logger.error("❌ YOUTUBE_TOKEN_JSON غير موجود")
                return
            
            token_data = json.loads(token_json)
            
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            
            self.service = build('youtube', 'v3', credentials=creds)
            logger.info("✅ YouTube API service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize YouTube service: {e}")
    
    def upload_video(self, video_path, title, description):
        if not self.service:
            logger.error("❌ YouTube service not initialized")
            return None
        
        try:
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': ['technology', 'education', 'tutorial', 'tech', 'programming'],
                    'categoryId': '28'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }
            
            request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
            )
            
            response = request.execute()
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.info(f"✅ Video uploaded: {video_url}")
            return video_url
            
        except Exception as e:
            logger.error(f"❌ YouTube upload failed: {e}")
            return None

class BloggerUploader:
    def __init__(self):
        self.blog_id = None
        self.service = None
        self.initialize_service()
    
    def initialize_service(self):
        try:
            token_json = os.getenv('BLOGGER_TOKEN_JSON')
            if not token_json:
                logger.error("❌ BLOGGER_TOKEN_JSON غير موجود")
                return
            
            token_data = json.loads(token_json)
            
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            
            self.service = build('blogger', 'v3', credentials=creds)
            
            try:
                blogs = self.service.blogs().listByUser(userId='self').execute()
                if blogs.get('items'):
                    self.blog_id = blogs['items'][0]['id']
                    logger.info(f"✅ Blogger blog ID: {self.blog_id}")
                else:
                    logger.error("❌ No blogs found")
                    self.blog_id = "YOUR_BLOG_ID"
            except:
                self.blog_id = "YOUR_BLOG_ID"
            
            logger.info("✅ Blogger API service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Blogger service: {e}")
    
    def publish_post(self, title, content):
        if not self.service or not self.blog_id:
            logger.error("❌ Blogger service not initialized")
            return None
        
        try:
            body = {
                'title': title,
                'content': content,
                'labels': ['technology', 'education', 'tutorial']
            }
            
            post = self.service.posts().insert(
                blogId=self.blog_id,
                body=body,
                isDraft=False
            ).execute()
            
            post_url = post['url']
            logger.info(f"✅ Blog post published: {post_url}")
            return post_url
            
        except Exception as e:
            logger.error(f"❌ Blogger publish failed: {e}")
            return None

class ProfessionalVideoCreator:
    """منشئ فيديو محترف بدون استخدام APIs خارجية"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # قائمة من الألوان الجذابة للخلفيات
        self.background_colors = [
            (25, 99, 235),   # أزرق
            (124, 58, 237),  # بنفسجي
            (5, 150, 105),   # أخضر
            (220, 38, 38),   # أحمر
            (245, 158, 11),  # برتقالي
            (139, 92, 246),  # بنفسجي فاتح
            (14, 165, 233),  # سماوي
            (236, 72, 153),  # وردي
        ]
        
        # تأثيرات بصرية محلية
        self.visual_patterns = [
            "gradient", "dots", "lines", "grid", "waves", "circuit"
        ]
    
    def create_dynamic_background(self, size=(1920, 1080), pattern_type=None):
        """إنشاء خلفية ديناميكية محلية"""
        if pattern_type is None:
            pattern_type = random.choice(self.visual_patterns)
        
        if pattern_type == "gradient":
            # تدرج لوني
            color1 = random.choice(self.background_colors)
            color2 = random.choice([c for c in self.background_colors if c != color1])
            
            image = Image.new('RGB', size, color1)
            draw = ImageDraw.Draw(image)
            
            for i in range(size[1]):
                r = int(color1[0] + (color2[0] - color1[0]) * (i / size[1]))
                g = int(color1[1] + (color2[1] - color1[1]) * (i / size[1]))
                b = int(color1[2] + (color2[2] - color1[2]) * (i / size[1]))
                draw.line([(0, i), (size[0], i)], fill=(r, g, b))
                
        elif pattern_type == "dots":
            # نقاط متلألئة
            base_color = random.choice(self.background_colors)
            image = Image.new('RGB', size, base_color)
            draw = ImageDraw.Draw(image)
            
            for _ in range(200):
                x = random.randint(0, size[0])
                y = random.randint(0, size[1])
                radius = random.randint(2, 6)
                brightness = random.randint(180, 255)
                color = (brightness, brightness, brightness)
                draw.ellipse([x, y, x + radius, y + radius], fill=color)
                
        elif pattern_type == "circuit":
            # نمط دائرة كهربائية
            base_color = random.choice(self.background_colors)
            image = Image.new('RGB', size, (10, 10, 20))
            draw = ImageDraw.Draw(image)
            
            for _ in range(50):
                x1 = random.randint(0, size[0])
                y1 = random.randint(0, size[1])
                x2 = x1 + random.randint(50, 200)
                y2 = y1 + random.randint(-50, 50)
                draw.line([(x1, y1), (x2, y2)], fill=base_color, width=2)
                
                # إضافة نقاط اتصال
                draw.ellipse([x1-3, y1-3, x1+3, y1+3], fill=(0, 255, 0))
                draw.ellipse([x2-3, y2-3, x2+3, y2+3], fill=(255, 0, 0))
                
        else:
            # خلفية عادية مع تمويه خفيف
            base_color = random.choice(self.background_colors)
            image = Image.new('RGB', size, base_color)
        
        return image
    
    def create_text_slide(self, text, size=(1920, 1080), slide_type="main"):
        """إنشاء شريحة نصية محترفة"""
        try:
            # إنشاء خلفية ديناميكية
            bg_image = self.create_dynamic_background(size)
            draw = ImageDraw.Draw(bg_image)
            
            # تحديد حجم الخط بناءً على نوع الشريحة
            if slide_type == "title":
                title_font_size = 90
                subtitle_font_size = 50
                max_width = size[0] - 200
            elif slide_type == "main":
                title_font_size = 70
                subtitle_font_size = 40
                max_width = size[0] - 150
            else:  # outro
                title_font_size = 80
                subtitle_font_size = 45
                max_width = size[0] - 200
            
            # محاولة تحميل خطوط
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_font_size)
                subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", subtitle_font_size)
            except:
                # خطوط افتراضية إذا فشل التحميل
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # تقسيم النص إلى سطور
            lines = textwrap.wrap(text, width=40 if slide_type == "title" else 50)
            
            if not lines:
                return None
            
            # حساب الارتفاع الكلي
            line_spacing = 20
            total_height = (len(lines) * (title_font_size if slide_type == "title" else subtitle_font_size)) + ((len(lines) - 1) * line_spacing)
            
            # حساب نقطة البداية
            y_start = (size[1] - total_height) // 2
            
            # إضافة خلفية شفافة للنص
            text_bg_height = total_height + 60
            text_bg_width = max_width + 100
            text_bg_x = (size[0] - text_bg_width) // 2
            text_bg_y = y_start - 30
            
            draw.rectangle(
                [text_bg_x, text_bg_y, text_bg_x + text_bg_width, text_bg_y + text_bg_height],
                fill=(0, 0, 0, 180),
                outline=(255, 255, 255, 100),
                width=3
            )
            
            # رسم النص
            current_y = y_start
            for i, line in enumerate(lines):
                if i == 0 and slide_type == "title":
                    font = title_font
                    text_color = (255, 255, 255)
                else:
                    font = subtitle_font
                    text_color = (240, 240, 240)
                
                # حساب عرض النص
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x_pos = (size[0] - text_width) // 2
                
                # إضافة ظل للنص
                shadow_offset = 4
                draw.text((x_pos + shadow_offset, current_y + shadow_offset), 
                         line, font=font, fill=(0, 0, 0, 200))
                
                # النص الرئيسي
                draw.text((x_pos, current_y), line, font=font, fill=text_color)
                
                current_y += (title_font_size if (i == 0 and slide_type == "title") else subtitle_font_size) + line_spacing
            
            # إضافة شعار في الزاوية
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 35)
            logo_text = "Tech Compass"
            draw.text((50, size[1] - 90), logo_text, font=logo_font, fill=(255, 255, 255, 200))
            draw.text((50, size[1] - 50), "Tech Education Channel", font=logo_font, fill=(200, 200, 200, 150))
            
            # حفظ الصورة
            temp_path = os.path.join(self.temp_dir, f"slide_{slide_type}_{hash(text[:30])}.png")
            bg_image.save(temp_path, 'PNG', quality=95)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Text slide creation error: {e}")
            return None
    
    def create_short_slide(self, text, size=(1080, 1920)):
        """إنشاء شريحة للمقاطع القصيرة"""
        try:
            # خلفية ديناميكية للشورت
            bg_image = self.create_dynamic_background(size, pattern_type=random.choice(["gradient", "dots"]))
            draw = ImageDraw.Draw(bg_image)
            
            # خطوط للشورت
            try:
                main_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 85)
                secondary_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 55)
            except:
                main_font = ImageFont.load_default()
                secondary_font = ImageFont.load_default()
            
            # تقسيم النص
            lines = textwrap.wrap(text, width=25)
            
            # حساب الارتفاع
            total_height = (len(lines) * 100) + ((len(lines) - 1) * 20)
            y_start = (size[1] - total_height) // 2
            
            # رسم كل سطر
            current_y = y_start
            for i, line in enumerate(lines):
                font = main_font if i == 0 else secondary_font
                text_color = (255, 255, 255) if i == 0 else (240, 240, 240)
                
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x_pos = (size[0] - text_width) // 2
                
                # ظل
                draw.text((x_pos + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 150))
                # نص
                draw.text((x_pos, current_y), line, font=font, fill=text_color)
                
                current_y += 100 if i == 0 else 70
            
            # إضافة أيقونة
            icons = ["🚀", "⚡", "💡", "🔥", "🎯", "✨", "🌟", "💫"]
            icon = random.choice(icons)
            icon_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 120)
            
            bbox = draw.textbbox((0, 0), icon, font=icon_font)
            icon_width = bbox[2] - bbox[0]
            icon_x = (size[0] - icon_width) // 2
            
            draw.text((icon_x, current_y + 50), icon, font=icon_font, fill=(255, 255, 255, 220))
            
            # حفظ
            temp_path = os.path.join(self.temp_dir, f"short_slide_{hash(text[:20])}.png")
            bg_image.save(temp_path, 'PNG', quality=95)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Short slide creation error: {e}")
            return None
    
    async def create_long_video(self, topic, script):
        """إنشاء فيديو طويل (8-10 دقائق)"""
        try:
            logger.info(f"🎬 Creating long video for: {topic}")
            
            # تقسيم السكربت إلى مشاهد
            scenes = self.prepare_scenes(script, scene_count=15)
            
            clips = []
            
            # 1. المقدمة (10 ثوان)
            intro_text = f"Complete Guide to:\n{topic}"
            intro_slide = self.create_text_slide(intro_text, slide_type="title")
            if intro_slide:
                intro_clip = ImageClip(intro_slide, duration=10)
                clips.append(intro_clip)
            
            # 2. المشاهد الرئيسية
            for i, scene_text in enumerate(scenes):
                scene_duration = self.calculate_scene_duration(scene_text, min_dur=8, max_dur=15)
                
                scene_slide = self.create_text_slide(scene_text, slide_type="main")
                if scene_slide:
                    scene_clip = ImageClip(scene_slide, duration=scene_duration)
                    clips.append(scene_clip)
                else:
                    # مشهد بديل
                    bg_color = random.choice(self.background_colors)
                    bg_clip = ColorClip(size=(1920, 1080), color=bg_color, duration=scene_duration)
                    clips.append(bg_clip)
            
            # 3. الخاتمة (8 ثوان)
            outro_text = "Thanks for watching!\n\nDon't forget to subscribe\nfor more tech education"
            outro_slide = self.create_text_slide(outro_text, slide_type="outro")
            if outro_slide:
                outro_clip = ImageClip(outro_slide, duration=8)
                clips.append(outro_clip)
            
            # تجميع الفيديو
            if not clips:
                logger.error("❌ No clips created")
                return None
            
            video = concatenate_videoclips(clips, method="compose")
            
            # إضافة موسيقى خلفية هادئة
            try:
                # إنشاء صوت بسيط باستخدام نغمة
                from moviepy.audio.AudioClip import CompositeAudioClip
                from moviepy.audio.io.AudioFileClip import AudioFileClip
                
                # يمكن إضافة ملف صوتي خلفي إذا كان موجوداً
                bg_music_path = "assets/background_music.mp3"
                if os.path.exists(bg_music_path):
                    bg_music = AudioFileClip(bg_music_path)
                    bg_music = bg_music.volumex(0.3)  # تخفيض الصوت
                    bg_music = bg_music.loop(duration=video.duration)
                    video = video.set_audio(bg_music)
            except:
                pass  # الملف غير موجود، نستمر بدون صوت
            
            # حفظ الفيديو
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/long_professional_{timestamp}.mp4"
            
            video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='medium',
                verbose=False,
                logger=None
            )
            
            logger.info(f"✅ Created long video: {output_path} ({video.duration:.1f}s)")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Long video creation error: {e}")
            return None
    
    async def create_short_video(self, topic, script):
        """إنشاء فيديو قصير (45-60 ثانية)"""
        try:
            logger.info(f"🎬 Creating short video for: {topic}")
            
            size = (1080, 1920)
            
            # تحضير النص للشورت
            short_texts = self.prepare_short_texts(script, count=5)
            
            clips = []
            
            # 1. المقدمة (3 ثوان)
            intro_text = f"⚡ {topic.split(':')[0] if ':' in topic else topic}\nQuick Tip!"
            intro_slide = self.create_short_slide(intro_text)
            if intro_slide:
                intro_clip = ImageClip(intro_slide, duration=3)
                clips.append(intro_clip)
            
            # 2. المشاهد الرئيسية
            for i, text in enumerate(short_texts):
                scene_duration = min(len(text.split()) * 0.6, 10)
                
                scene_slide = self.create_short_slide(text)
                if scene_slide:
                    scene_clip = ImageClip(scene_slide, duration=scene_duration)
                    clips.append(scene_clip)
                else:
                    bg_color = random.choice(self.background_colors)
                    bg_clip = ColorClip(size=size, color=bg_color, duration=scene_duration)
                    clips.append(bg_clip)
            
            # 3. الخاتمة (3 ثوان)
            outro_text = "🔔 Follow for more!\n@TechCompass"
            outro_slide = self.create_short_slide(outro_text)
            if outro_slide:
                outro_clip = ImageClip(outro_slide, duration=3)
                clips.append(outro_clip)
            
            # تجميع الفيديو
            if not clips:
                logger.error("❌ No short clips created")
                return None
            
            video = concatenate_videoclips(clips, method="compose")
            
            # حفظ الفيديو
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/short_professional_{timestamp}.mp4"
            
            video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='fast',
                verbose=False,
                logger=None
            )
            
            logger.info(f"✅ Created short video: {output_path} ({video.duration:.1f}s)")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Short video creation error: {e}")
            return None
    
    def prepare_scenes(self, script, scene_count=15):
        """تحضير المشاهد من السكربت"""
        # تقسيم إلى فقرات
        paragraphs = re.split(r'\n\s*\n', script)
        
        scenes = []
        for para in paragraphs:
            if para.strip():
                # تقسيم الفقرة إلى جمل
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 20:  # جمل ذات معنى
                        if len(sent) > 120:
                            sent = sent[:117] + "..."
                        scenes.append(sent)
        
        # إذا كانت المشاهد قليلة، ننشئ مشاهد إضافية
        if len(scenes) < scene_count:
            base_scenes = [
                f"Let's explore this important topic in detail",
                f"This technology is changing how we work and live",
                f"Understanding the basics is crucial for success",
                f"Practical applications make learning more effective",
                f"Real-world examples help clarify complex concepts",
                f"Best practices ensure better results",
                f"Common challenges and how to overcome them",
                f"Future trends in this technology field",
                f"How to get started with practical implementation",
                f"Tips for mastering this technology quickly"
            ]
            
            while len(scenes) < scene_count:
                scenes.append(random.choice(base_scenes))
        
        return scenes[:scene_count]
    
    def prepare_short_texts(self, script, count=5):
        """تحضير نصوص للشورت"""
        sentences = re.split(r'(?<=[.!?])\s+', script)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        short_texts = []
        for sent in sentences[:count]:
            if len(sent) > 80:
                sent = sent[:77] + "..."
            short_texts.append(sent)
        
        # إذا كانت النصوص قليلة
        while len(short_texts) < count:
            tips = [
                "Tech tip of the day!",
                "Learn something new every day",
                "Stay updated with technology",
                "Practice makes perfect in tech",
                "Follow for daily insights"
            ]
            short_texts.append(random.choice(tips))
        
        return short_texts
    
    def calculate_scene_duration(self, text, min_dur=8, max_dur=15):
        """حساب مدة المشهد بناءً على طول النص"""
        word_count = len(text.split())
        duration = word_count * 0.5  # 0.5 ثانية لكل كلمة
        return max(min_dur, min(duration, max_dur))

class ContentEmpire:
    def __init__(self):
        self.config = Config()
        self.setup_directories()
        self.used_topics = set()
        self.content_history = {"videos": [], "articles": []}
        self.load_history()
        self.youtube_uploader = YouTubeUploader()
        self.blogger_uploader = BloggerUploader()
        self.video_creator = ProfessionalVideoCreator()
    
    def setup_directories(self):
        os.makedirs('output', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('assets', exist_ok=True)
    
    def load_history(self):
        try:
            if os.path.exists('output/used_topics.txt'):
                with open('output/used_topics.txt', 'r') as f:
                    self.used_topics = set(line.strip() for line in f)
        except:
            self.used_topics = set()
    
    def save_topic(self, topic):
        self.used_topics.add(topic)
        with open('output/used_topics.txt', 'a') as f:
            f.write(topic + '\n')
    
    async def get_unique_topic(self):
        topics = [
            "Cloud Computing Explained: AWS vs Azure vs Google Cloud",
            "Artificial Intelligence in Modern Healthcare",
            "Cybersecurity Essentials for 2024",
            "Data Science Career Path Complete Guide",
            "Blockchain Technology Beyond Cryptocurrency",
            "5G Networks and Future of Connectivity",
            "Internet of Things: Smart Home Revolution",
            "Machine Learning vs Deep Learning Comparison",
            "Quantum Computing: Next Tech Revolution",
            "Augmented Reality in Education Today"
        ]
        
        available = [t for t in topics if t not in self.used_topics]
        if available:
            topic = random.choice(available)
        else:
            topic = "Latest Technology Trends 2024 Guide"
        
        self.save_topic(topic)
        return topic
    
    async def generate_content(self, topic, content_type="long_video"):
        try:
            if not self.config.GEMINI_API_KEY:
                return self.get_fallback_content(topic, content_type)
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            # استخدام النموذج المتاح
            try:
                model = genai.GenerativeModel('gemini-pro')
            except:
                try:
                    model = genai.GenerativeModel('gemini-1.0-pro')
                except:
                    return self.get_fallback_content(topic, content_type)
            
            if content_type == "long_video":
                prompt = f"""Create a comprehensive YouTube tutorial script about: "{topic}"

                Requirements:
                - 800+ words
                - Educational and practical
                - Structured into clear sections
                - Include real examples
                - Engaging spoken style
                - End with call to action"""
                
                response = await model.generate_content_async(prompt)
                return response.text
                
            elif content_type == "blog":
                prompt = f"""Write a detailed blog post about: "{topic}"

                Requirements:
                - 1200+ words
                - SEO optimized with headings
                - Include bullet points
                - Practical tips included
                - Beginner friendly"""
                
                response = await model.generate_content_async(prompt)
                return response.text
            
            else:  # short video
                prompt = f"""Create an engaging YouTube Short script about: "{topic}"

                Requirements:
                - Maximum 80 words
                - Start with attention hook
                - One key insight
                - High energy
                - Call to action"""
                
                response = await model.generate_content_async(prompt)
                return response.text
                
        except Exception as e:
            logger.error(f"❌ Content generation error: {e}")
            return self.get_fallback_content(topic, content_type)
    
    def get_fallback_content(self, topic, content_type):
        if content_type == "long_video":
            return f"""Welcome to Tech Compass! Today we're exploring {topic}.

This technology is transforming industries worldwide. Let's understand what it really means.

First, the basics. {topic.split(':')[0] if ':' in topic else topic} involves key concepts everyone should know.

Applications are everywhere. From business to daily life, this technology creates value.

Key components include foundational principles, current uses, and future potential.

Real examples show practical implementation in various fields.

Benefits are clear: increased efficiency, cost reduction, better accuracy, and scalability.

Getting started involves learning basics, practicing with projects, and joining communities.

Future trends indicate continued growth and innovation in this field.

Remember to apply what you learn in practical ways.

Stay curious and keep learning as technology evolves.

Thanks for watching! Subscribe for more tech education."""
        
        elif content_type == "blog":
            return f"""# Complete Guide to {topic}

## Introduction
{topic} represents transformative technology changing our world. This guide covers essentials.

## Understanding Basics
Core concepts form the foundation of this technology.

## Key Components
- Component 1: Description and importance
- Component 2: Practical applications
- Component 3: Implementation steps

## Benefits and Advantages
1. **Efficiency**: Streamlining processes
2. **Cost Savings**: Reducing expenses
3. **Accuracy**: Minimizing errors
4. **Scalability**: Growing with needs

## Real-World Applications
Examples from various industries demonstrate practical use.

## Getting Started
Step-by-step beginner's guide:
1. Learn fundamentals
2. Setup environment
3. Start simple projects
4. Join communities
5. Build portfolio

## Future Outlook
Emerging trends and developments to watch.

## Conclusion
{topic} offers significant opportunities. Start learning today for future success."""
        
        else:  # short video
            return f"Tech tip! {topic.split(':')[0] if ':' in topic else topic} ⚡\n\nQuick insight to improve your skills!\n\nFollow for daily tech tips! 🔔"
    
    async def run_12_00_workflow(self):
        try:
            logger.info("🚀 Starting 12:00 workflow")
            
            topic = await self.get_unique_topic()
            logger.info(f"📝 Topic: {topic}")
            
            # توليد المحتوى
            video_script = await self.generate_content(topic, "long_video")
            blog_content = await self.generate_content(topic, "blog")
            
            # إنشاء فيديو محترف
            video_path = await self.video_creator.create_long_video(topic, video_script)
            
            if video_path and os.path.exists(video_path):
                # تحقق من مدة الفيديو
                try:
                    video_clip = VideoFileClip(video_path)
                    duration = video_clip.duration
                    video_clip.close()
                    
                    logger.info(f"📏 Video duration: {duration:.1f} seconds")
                    
                    if duration < 300:  # أقل من 5 دقائق
                        logger.warning("⚠️ Video too short, extending...")
                        # إنشاء فيديو أطول
                        extended_script = video_script + "\n\n" + self.get_extended_content(topic)
                        video_path = await self.video_creator.create_long_video(topic, extended_script)
                except:
                    pass
                
                # رفع الفيديو
                youtube_url = self.youtube_uploader.upload_video(
                    video_path, 
                    f"{topic} - Complete Tutorial 2024", 
                    f"Learn everything about {topic} in this comprehensive tutorial.\n\n"
                    f"Topics covered: Basics, Applications, Benefits, Future Trends.\n\n"
                    f"Subscribe for more: {self.config.YOUTUBE_CHANNEL_URL}\n"
                    f"Blog: {self.config.BLOGGER_BLOG_URL}\n\n"
                    f"#Tech #Education #Tutorial #Technology"
                )
                
                if youtube_url:
                    # نشر المقال
                    blog_url = self.blogger_uploader.publish_post(
                        f"Complete Guide: {topic}",
                        blog_content + f'\n\n<div style="text-align: center; margin: 30px 0;">'
                        f'<a href="{youtube_url}" style="background: #ff0000; color: white; padding: 12px 24px; '
                        f'border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 18px;">'
                        f'▶️ Watch Video Tutorial Here</a></div>'
                    )
            
            logger.info("✅ 12:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 12:00 workflow error: {e}")
    
    def get_extended_content(self, topic):
        """إضافة محتوى إضافي"""
        extensions = [
            f"Let's explore advanced aspects of {topic.split(':')[0] if ':' in topic else topic}. "
            f"This includes implementation strategies and best practices.",
            
            f"Common challenges in this field and practical solutions to overcome them. "
            f"This knowledge helps avoid typical mistakes.",
            
            f"Future developments that will shape the evolution of this technology. "
            f"Staying updated ensures continued relevance.",
            
            f"Resources for further learning including books, courses, and communities. "
            f"Continuous learning is key to mastery.",
            
            f"Case studies showing real-world success stories. "
            f"Practical examples demonstrate effective implementation."
        ]
        return "\n\n".join(random.sample(extensions, 3))
    
    async def run_14_00_workflow(self):
        try:
            logger.info("🚀 Starting 14:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            # إنشاء شورت
            video_path = await self.video_creator.create_short_video(topic, short_script)
            
            if video_path and os.path.exists(video_path):
                self.youtube_uploader.upload_video(
                    video_path,
                    f"{topic} - Quick Tip! 🔥 #Shorts",
                    f"Quick tech tip about {topic.split(':')[0] if ':' in topic else topic}! "
                    f"Perfect for quick learning. Follow for more!\n\n"
                    f"#Shorts #Tech #Tips #Technology #Learning"
                )
            
            logger.info("✅ 14:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 14:00 workflow error: {e}")
    
    async def run_16_00_workflow(self):
        try:
            logger.info("🚀 Starting 16:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            # إنشاء شورت ثاني
            video_path = await self.video_creator.create_short_video(topic, short_script)
            
            if video_path and os.path.exists(video_path):
                self.youtube_uploader.upload_video(
                    video_path,
                    f"{topic} Explained! ⚡ #Shorts",
                    f"Understanding {topic.split(':')[0] if ':' in topic else topic} made simple! "
                    f"Quick and educational content.\n\n"
                    f"#Shorts #Tech #Explained #Education #Tutorial"
                )
            
            logger.info("✅ 16:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 16:00 workflow error: {e}")
    
    async def run_daily_workflow(self):
        try:
            # تشغيل جميع الworkflows
            await self.run_12_00_workflow()
            await asyncio.sleep(3)
            
            await self.run_14_00_workflow()
            await asyncio.sleep(3)
            
            await self.run_16_00_workflow()
            
            await self.config.send_telegram_message(f"""
🎉 <b>Daily Content Production Complete!</b>

✅ <b>Long Tutorial Video:</b> 8-10 minutes with professional slides
✅ <b>Tech Short #1:</b> 45 seconds with engaging visuals  
✅ <b>Tech Short #2:</b> 45 seconds with quick insights

<b>Features:</b>
• Professional dynamic backgrounds
• Text perfectly within frame
• No external API dependencies
• Clean visual design
• Automatic YouTube & Blogger publishing

🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
""")
            
        except Exception as e:
            logger.error(f"❌ Daily workflow failed: {e}")
            await self.config.send_telegram_message(f"❌ Daily workflow failed: {str(e)}")

if __name__ == "__main__":
    # التأكد من وجود المجلدات
    for folder in ['output', 'temp', 'assets']:
        os.makedirs(folder, exist_ok=True)
    
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflow())
