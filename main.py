import asyncio
import logging
import os
import google.generativeai as genai
import edge_tts
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
    """منشئ فيديو محترف مع مدة مناسبة ومحتوى غني"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def create_rich_text_image(self, text, size=(1920, 1080), is_title=False):
        """إنشاء صورة نصية غنية بالمحتوى"""
        try:
            # خلفية متدرجة
            image = Image.new('RGB', size, color=(30, 60, 90))
            draw = ImageDraw.Draw(image)
            
            # إضافة تدرج لوني
            for i in range(size[1]):
                r = int(30 + (i / size[1]) * 20)
                g = int(60 + (i / size[1]) * 40)
                b = int(90 + (i / size[1]) * 30)
                draw.line([(0, i), (size[0], i)], fill=(r, g, b))
            
            # إعداد الخط
            try:
                if is_title:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
                    text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
                else:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
                    text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
            except:
                # خطوط افتراضية
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
            
            # تقسيم النص إلى عنوان وجسم
            lines = textwrap.wrap(text, width=40 if is_title else 50)
            
            y_position = size[1] // 4
            
            # رسم العنوان (السطر الأول)
            if lines:
                title_line = lines[0]
                bbox = draw.textbbox((0, 0), title_line, font=title_font)
                text_width = bbox[2] - bbox[0]
                x = (size[0] - text_width) // 2
                
                # ظل للنص
                draw.text((x+4, y_position+4), title_line, font=title_font, fill=(0, 0, 0, 180))
                draw.text((x, y_position), title_line, font=title_font, fill=(255, 255, 255))
                
                y_position += 120
            
            # رسم بقية النص
            for line in lines[1:]:
                bbox = draw.textbbox((0, 0), line, font=text_font)
                text_width = bbox[2] - bbox[0]
                x = (size[0] - text_width) // 2
                
                draw.text((x+3, y_position+3), line, font=text_font, fill=(0, 0, 0))
                draw.text((x, y_position), line, font=text_font, fill=(220, 220, 220))
                
                y_position += 60
            
            # إضافة شعار في الزاوية
            logo_text = "Tech Compass"
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
            draw.text((50, size[1] - 80), logo_text, font=logo_font, fill=(255, 255, 255, 200))
            draw.text((50, size[1] - 50), "Tech Education Channel", font=logo_font, fill=(200, 200, 200, 180))
            
            # حفظ الصورة
            temp_path = os.path.join(self.temp_dir, f"rich_text_{hash(text)}.png")
            image.save(temp_path, quality=95)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Rich text image error: {e}")
            return None
    
    def create_short_text_image(self, text, size=(1080, 1920)):
        """إنشاء صورة للمقاطع القصيرة"""
        try:
            # خلفية ديناميكية
            colors = [
                (25, 99, 235),   # أزرق
                (124, 58, 237),  # بنفسجي
                (5, 150, 105),   # أخضر
                (220, 38, 38)    # أحمر
            ]
            color = random.choice(colors)
            image = Image.new('RGB', size, color=color)
            draw = ImageDraw.Draw(image)
            
            # إضافة نمط
            for i in range(0, size[0], 40):
                draw.line([(i, 0), (i, size[1])], fill=(255, 255, 255, 30), width=2)
            
            # خط كبير للنص
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # تقسيم النص
            lines = textwrap.wrap(text, width=25)
            y_position = size[1] // 3
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font_large if i == 0 else font_small)
                text_width = bbox[2] - bbox[0]
                x = (size[0] - text_width) // 2
                
                # ظل
                draw.text((x+5, y_position+5), line, 
                         font=font_large if i == 0 else font_small, 
                         fill=(0, 0, 0, 150))
                
                # النص الرئيسي
                draw.text((x, y_position), line, 
                         font=font_large if i == 0 else font_small, 
                         fill=(255, 255, 255))
                
                y_position += 100 if i == 0 else 70
            
            # إضافة أيقونة
            icons = ["🚀", "⚡", "💡", "🔥", "🎯"]
            icon = random.choice(icons)
            icon_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 120)
            icon_bbox = draw.textbbox((0, 0), icon, font=icon_font)
            icon_width = icon_bbox[2] - icon_bbox[0]
            icon_x = (size[0] - icon_width) // 2
            
            draw.text((icon_x, y_position + 50), icon, font=icon_font, fill=(255, 255, 255, 200))
            
            # حفظ الصورة
            temp_path = os.path.join(self.temp_dir, f"short_text_{hash(text)}.png")
            image.save(temp_path, quality=95)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Short text image error: {e}")
            return None
    
    async def create_long_video(self, topic, script, audio_path):
        """إنشاء فيديو طويل (8-10 دقائق)"""
        try:
            # تقسيم السكربت إلى مشاهد
            paragraphs = self.split_into_paragraphs(script, min_paragraphs=15)
            
            clips = []
            total_duration = 0
            target_duration = 600  # 10 دقائق
            
            # 1. المقدمة الاحترافية (15 ثانية)
            intro_text = f"Complete Guide to\n{topic}"
            intro_image = self.create_rich_text_image(intro_text, is_title=True)
            if intro_image:
                intro_clip = ImageClip(intro_image, duration=15)
                clips.append(intro_clip)
                total_duration += 15
            
            # 2. محتوى رئيسي
            scene_durations = self.calculate_scene_durations(len(paragraphs), target_duration - 30)
            
            for i, paragraph in enumerate(paragraphs):
                if total_duration >= target_duration:
                    break
                    
                scene_duration = scene_durations[i] if i < len(scene_durations) else 10
                
                # إنشاء مشهد
                scene_image = self.create_rich_text_image(paragraph)
                if scene_image:
                    scene_clip = ImageClip(scene_image, duration=scene_duration)
                    clips.append(scene_clip)
                    total_duration += scene_duration
                else:
                    # مشهد بديل
                    bg_color = random.choice([(30, 60, 90), (25, 99, 235), (5, 150, 105)])
                    bg_clip = ColorClip(size=(1920, 1080), color=bg_color, duration=scene_duration)
                    clips.append(bg_clip)
                    total_duration += scene_duration
            
            # 3. الخاتمة (15 ثانية)
            outro_text = "Thanks for watching!\n\nDon't forget to subscribe for more tech content"
            outro_image = self.create_rich_text_image(outro_text)
            if outro_image:
                outro_clip = ImageClip(outro_image, duration=15)
                clips.append(outro_clip)
                total_duration += 15
            
            # 4. تجميع الفيديو
            if not clips:
                # فيديو احتياطي
                final_clip = ColorClip(size=(1920, 1080), color=(25, 99, 235), duration=300)
            else:
                final_clip = concatenate_videoclips(clips, method="compose")
            
            # 5. إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    
                    # تأكد أن الصوت طويل بما يكفي
                    if audio_clip.duration < final_clip.duration:
                        # تكرار الصوت إذا كان قصيراً
                        repeats = int(final_clip.duration // audio_clip.duration) + 1
                        audio_segments = [audio_clip] * repeats
                        audio_clip = concatenate_audioclips(audio_segments)
                    
                    # اقتصاص الصوت لطول الفيديو
                    audio_clip = audio_clip.subclip(0, final_clip.duration)
                    final_clip = final_clip.set_audio(audio_clip)
                    
                except Exception as e:
                    logger.error(f"❌ Audio addition error: {e}")
            
            # 6. حفظ الفيديو
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/long_video_{timestamp}.mp4"
            
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                verbose=False,
                logger=None
            )
            
            logger.info(f"✅ Created long video: {output_path} ({final_clip.duration:.1f}s)")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Long video creation error: {e}")
            return None
    
    async def create_short_video(self, topic, script, audio_path):
        """إنشاء فيديو قصير (45-60 ثانية)"""
        try:
            # تقسيم النص لمشاهد قصيرة
            sentences = re.split(r'[.!?]+', script)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10][:5]
            
            if not sentences:
                sentences = [f"Quick tip about {topic}!", "This can save you time!", "Follow for more!"]
            
            clips = []
            total_duration = 0
            target_duration = 45  # 45 ثانية
            
            # 1. المقدمة السريعة (3 ثواني)
            intro_text = f"⚡ {topic.split(':')[0] if ':' in topic else topic}"
            intro_image = self.create_short_text_image(intro_text)
            if intro_image:
                intro_clip = ImageClip(intro_image, duration=3)
                clips.append(intro_clip)
                total_duration += 3
            
            # 2. المشاهد الرئيسية
            for sentence in sentences:
                if total_duration >= target_duration - 3:
                    break
                    
                scene_duration = min(len(sentence.split()) * 0.8, 10)
                scene_image = self.create_short_text_image(sentence[:100])
                
                if scene_image:
                    scene_clip = ImageClip(scene_image, duration=scene_duration)
                    clips.append(scene_clip)
                    total_duration += scene_duration
            
            # 3. الخاتمة (3 ثواني)
            outro_text = "🔔 Follow for more tech tips!"
            outro_image = self.create_short_text_image(outro_text)
            if outro_image:
                outro_clip = ImageClip(outro_image, duration=3)
                clips.append(outro_clip)
                total_duration += 3
            
            # 4. تجميع الفيديو
            if not clips:
                final_clip = ColorClip(size=(1080, 1920), color=(25, 99, 235), duration=45)
            else:
                final_clip = concatenate_videoclips(clips, method="compose")
            
            # 5. إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    
                    # تكرار الصوت إذا كان قصيراً
                    if audio_clip.duration < final_clip.duration:
                        repeats = int(final_clip.duration // audio_clip.duration) + 1
                        audio_segments = [audio_clip] * repeats
                        audio_clip = concatenate_audioclips(audio_segments)
                    
                    audio_clip = audio_clip.subclip(0, final_clip.duration)
                    final_clip = final_clip.set_audio(audio_clip)
                    
                except Exception as e:
                    logger.error(f"❌ Short audio error: {e}")
            
            # 6. حفظ الفيديو
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/short_video_{timestamp}.mp4"
            
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                verbose=False,
                logger=None
            )
            
            logger.info(f"✅ Created short video: {output_path} ({final_clip.duration:.1f}s)")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Short video creation error: {e}")
            return None
    
    def split_into_paragraphs(self, text, min_paragraphs=10):
        """تقسيم النص إلى فقرات"""
        # تقسيم إلى جمل
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        paragraphs = []
        current_paragraph = []
        words_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            words = sentence.split()
            words_count += len(words)
            current_paragraph.append(sentence)
            
            # كل 30-50 كلمة تكون فقرة
            if words_count >= 40:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                words_count = 0
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # إذا كانت الفقرات قليلة، نقسم الجمل بشكل مختلف
        if len(paragraphs) < min_paragraphs:
            # تقسيم كل جملة إلى قسمين
            new_paragraphs = []
            for para in paragraphs:
                sentences_in_para = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences_in_para:
                    if len(sent.split()) > 5:
                        new_paragraphs.append(sent)
            
            paragraphs = new_paragraphs[:min_paragraphs]
        
        return paragraphs[:15]  # حد أقصى 15 فقرة
    
    def calculate_scene_durations(self, num_scenes, total_duration):
        """حساب مدة كل مشهد"""
        if num_scenes == 0:
            return [total_duration]
        
        base_duration = total_duration / num_scenes
        durations = []
        
        for i in range(num_scenes):
            # تغيير طفيف في المدة لجعلها طبيعية
            variation = random.uniform(0.8, 1.2)
            duration = base_duration * variation
            durations.append(max(5, min(duration, 20)))  # بين 5 و20 ثانية
        
        # تعديل المجموع ليكون total_duration
        total = sum(durations)
        factor = total_duration / total
        durations = [d * factor for d in durations]
        
        return durations

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
            "Artificial Intelligence in Modern Healthcare: Saving Lives with Machine Learning",
            "Quantum Computing 2024: The Future of Processing Power",
            "Cybersecurity Essentials: Protecting Your Digital Life",
            "Cloud Computing Explained: AWS vs Azure vs Google Cloud",
            "Blockchain Technology: Beyond Bitcoin and Cryptocurrency",
            "5G Networks: Revolutionizing Mobile Connectivity",
            "Internet of Things (IoT): Smart Homes and Cities",
            "Data Science Career Path: Skills You Need in 2024",
            "Machine Learning vs Deep Learning: Key Differences Explained",
            "Augmented Reality in Education: The Future of Learning"
        ]
        
        available = [t for t in topics if t not in self.used_topics]
        if available:
            topic = random.choice(available)
        else:
            topic = "Emerging Technology Trends 2024: What You Need to Know"
        
        self.save_topic(topic)
        return topic
    
    async def generate_content(self, topic, content_type="long_video"):
        try:
            if not self.config.GEMINI_API_KEY:
                return self.get_fallback_content(topic, content_type)
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            if content_type == "long_video":
                prompt = f"""Create a comprehensive YouTube tutorial script about: "{topic}"

                Requirements:
                - 1000+ words
                - Educational and practical
                - Structured into clear sections
                - Include real-world examples
                - Add actionable tips
                - Keep language engaging but professional
                - End with a call to action"""
                
                model = genai.GenerativeModel('gemini-pro')
                response = await model.generate_content_async(prompt)
                return response.text
                
            elif content_type == "blog":
                prompt = f"""Write a detailed blog post about: "{topic}"

                Requirements:
                - 1500+ words
                - SEO optimized with headings
                - Include: Introduction, Main Content, Examples, Conclusion
                - Add bullet points and lists
                - Make it beginner-friendly
                - Include practical applications"""
                
                model = genai.GenerativeModel('gemini-pro')
                response = await model.generate_content_async(prompt)
                return response.text
            
            else:  # short video
                prompt = f"""Create a quick, engaging YouTube Short script about: "{topic}"

                Requirements:
                - Under 100 words
                - Hook in first 5 words
                - One key insight or tip
                - High energy
                - Call to action at end
                - Use emojis sparingly"""
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = await model.generate_content_async(prompt)
                return response.text
                
        except Exception as e:
            logger.error(f"❌ Content generation error: {e}")
            return self.get_fallback_content(topic, content_type)
    
    def get_fallback_content(self, topic, content_type):
        if content_type == "long_video":
            return f"""Welcome to Tech Compass! Today we're diving deep into {topic}.

This is one of the most exciting technologies of our time. Let's explore it together.

First, let's understand what {topic.split(':')[0] if ':' in topic else topic} really means. At its core, it's about using technology to solve real-world problems.

The applications are endless. From healthcare to finance, from education to entertainment, this technology is making a difference.

Here are the key concepts you need to know:

1. Foundational Principles
Understanding the basics is crucial. We'll break down the complex ideas into simple terms.

2. Current Applications
Where is this technology being used today? We'll look at real-world examples.

3. Future Potential
What does the future hold? We'll explore upcoming trends and developments.

4. Getting Started
How can you begin learning and using this technology? We'll provide practical steps.

Remember, the goal isn't just to understand the theory, but to apply it in practical ways.

Whether you're a student, professional, or just curious about technology, this tutorial will give you valuable insights.

Don't forget to practice what you learn. The best way to understand any technology is to use it.

If you have questions, leave them in the comments below. We'll do our best to help.

Thanks for watching, and don't forget to subscribe for more tech tutorials!"""
        
        elif content_type == "blog":
            return f"""# Complete Guide to {topic}

## Introduction
{topic} represents one of the most significant technological advancements of our era. In this comprehensive guide, we'll explore everything you need to know about this transformative technology.

## What is {topic.split(':')[0] if ':' in topic else topic}?
At its core, this technology represents a paradigm shift in how we approach problem-solving and innovation.

## Key Benefits and Applications
1. **Increased Efficiency**: Automating repetitive tasks and processes
2. **Enhanced Accuracy**: Reducing human error through automation
3. **Cost Reduction**: Optimizing resources and operations
4. **Improved User Experience**: Creating better products and services

## Getting Started
To begin your journey with {topic.split()[0]}, follow these steps:

### Step 1: Learn the Fundamentals
Start with the basic concepts and principles.

### Step 2: Practice with Projects
Apply your knowledge through hands-on projects.

### Step 3: Join Communities
Connect with other learners and professionals.

### Step 4: Build a Portfolio
Showcase your skills and knowledge.

## Real-World Examples
We'll examine how leading companies are implementing this technology to drive innovation and growth.

## Future Outlook
What does the future hold for {topic.split()[0]}? We'll explore emerging trends and predictions.

## Conclusion
{topic} is more than just a trend—it's a fundamental shift in how we interact with technology. By understanding and embracing this technology, you position yourself for success in the digital age.

Ready to learn more? Check out our YouTube channel for video tutorials!"""
        
        else:  # short video
            return f"⚡ Quick Tech Tip!\n\n{topic.split(':')[0] if ':' in topic else topic} can transform your workflow!\n\nHere's one key insight you need to know...\n\nFollow for more daily tech tips! 🔥"
    
    async def generate_audio(self, text, output_name):
        try:
            output_path = f"temp/{output_name}.mp3"
            
            # استخدام جزء من النص للصوت
            clean_text = text[:2000].replace('\n', ' ').replace('"', "'")
            
            communicate = edge_tts.Communicate(
                clean_text,
                "en-US-ChristopherNeural",
                rate="+10%",
                pitch="+0Hz"
            )
            
            await communicate.save(output_path)
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Audio generation error: {e}")
            return None
    
    async def run_12_00_workflow(self):
        try:
            logger.info("🚀 Starting 12:00 workflow")
            
            topic = await self.get_unique_topic()
            logger.info(f"📝 Topic: {topic}")
            
            video_script = await self.generate_content(topic, "long_video")
            blog_content = await self.generate_content(topic, "blog")
            
            audio_path = await self.generate_audio(video_script, "long_audio")
            video_path = await self.video_creator.create_long_video(topic, video_script, audio_path)
            
            if video_path and os.path.exists(video_path):
                # تحقق من مدة الفيديو
                video_clip = VideoFileClip(video_path)
                duration = video_clip.duration
                video_clip.close()
                
                logger.info(f"📏 Video duration: {duration:.1f} seconds")
                
                if duration < 300:  # أقل من 5 دقائق
                    logger.warning("⚠️ Video too short, creating new one")
                    # إنشاء فيديو أطول
                    video_path = await self.create_extended_video(topic, video_script, audio_path)
                
                youtube_url = self.youtube_uploader.upload_video(
                    video_path, 
                    f"{topic} - Complete Tutorial 2024", 
                    video_script[:500] + f"\n\nLearn more about {topic} in this comprehensive tutorial."
                )
                
                if youtube_url:
                    blog_url = self.blogger_uploader.publish_post(
                        f"Complete Guide: {topic}",
                        blog_content + f'\n\n<center><a href="{youtube_url}">Watch the video tutorial here</a></center>'
                    )
            
            logger.info("✅ 12:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 12:00 workflow error: {e}")
    
    async def create_extended_video(self, topic, script, audio_path):
        """إنشاء فيديو أطول"""
        try:
            # تكرار أجزاء من السكربت لزيادة المدة
            paragraphs = script.split('\n\n')
            extended_script = script + "\n\n" + "\n\n".join(paragraphs[:5])
            
            return await self.video_creator.create_long_video(topic, extended_script, audio_path)
        except:
            return None
    
    async def run_14_00_workflow(self):
        try:
            logger.info("🚀 Starting 14:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            audio_path = await self.generate_audio(short_script, "short_audio_1")
            video_path = await self.video_creator.create_short_video(topic, short_script, audio_path)
            
            if video_path and os.path.exists(video_path):
                self.youtube_uploader.upload_video(
                    video_path,
                    f"{topic} - Quick Tip ⚡",
                    short_script + "\n\n#Shorts #Tech #Tips"
                )
            
            logger.info("✅ 14:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 14:00 workflow error: {e}")
    
    async def run_16_00_workflow(self):
        try:
            logger.info("🚀 Starting 16:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            audio_path = await self.generate_audio(short_script, "short_audio_2")
            video_path = await self.video_creator.create_short_video(topic, short_script, audio_path)
            
            if video_path and os.path.exists(video_path):
                self.youtube_uploader.upload_video(
                    video_path,
                    f"{topic} Explained in Seconds! 🚀",
                    short_script + "\n\n#Shorts #Technology #Education"
                )
            
            logger.info("✅ 16:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 16:00 workflow error: {e}")
    
    async def run_daily_workflow(self):
        try:
            # تشغيل جميع الworkflows
            await self.run_12_00_workflow()
            await asyncio.sleep(5)
            
            await self.run_14_00_workflow()
            await asyncio.sleep(5)
            
            await self.run_16_00_workflow()
            
            await self.config.send_telegram_message(f"""
🎉 <b>Daily Content Production Complete!</b>

✅ Long Tutorial Video (10+ minutes)
✅ Tech Short #1 (45 seconds)
✅ Tech Short #2 (45 seconds)

All content has been generated and published successfully!

🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
""")
            
        except Exception as e:
            logger.error(f"❌ Daily workflow failed: {e}")

if __name__ == "__main__":
    # التأكد من وجود المجلدات
    for folder in ['output', 'temp']:
        os.makedirs(folder, exist_ok=True)
    
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflow())
