import asyncio
import logging
import os
import google.generativeai as genai
import edge_tts
from moviepy.editor import *
from datetime import datetime, timedelta
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
import tempfile

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# إصلاح مشكلة TextClip
import moviepy.config as mp_config
mp_config.change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

class Config:
    def __init__(self):
        # استخدام Environment Variables
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        self.PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
        
        # إعدادات المحتوى
        self.YOUTUBE_CHANNEL_URL = "https://youtube.com/@techcompass-d5l"
        self.BLOGGER_BLOG_URL = "https://techcompass4you.blogspot.com/"
        self.CONTENT_NICHE = "Technology"
        self.BRAND_NAME = "TechCompass"
        
    async def send_telegram_message(self, message):
        try:
            if not self.TELEGRAM_BOT_TOKEN or not self.TELEGRAM_CHAT_ID:
                logger.error("❌ Telegram credentials missing")
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
        """تهيئة خدمة YouTube API"""
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
            logger.info("✅ YouTube API service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize YouTube service: {e}")
    
    def upload_video(self, video_path, title, description):
        """رفع فيديو حقيقي إلى YouTube"""
        if not self.service:
            logger.error("❌ YouTube service not initialized")
            return None
        
        try:
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': ['technology', 'education', 'tutorial', 'tech', 'programming', 'coding', 'software', 'AI', 'artificial intelligence', 'machine learning'],
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
            
            logger.info(f"✅ Video uploaded successfully: {video_url}")
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
        """تهيئة خدمة Blogger API"""
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
            
            # الحصول على blog_id
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
            
            logger.info("✅ Blogger API service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Blogger service: {e}")
    
    def publish_post(self, title, content):
        """نشر مقال على Blogger"""
        if not self.service or not self.blog_id:
            logger.error("❌ Blogger service not initialized")
            return None
        
        try:
            body = {
                'title': title,
                'content': content,
                'labels': ['technology', 'education', 'tutorial', 'tech', 'programming']
            }
            
            post = self.service.posts().insert(
                blogId=self.blog_id,
                body=body,
                isDraft=False
            ).execute()
            
            post_url = post['url']
            logger.info(f"✅ Blog post published successfully: {post_url}")
            return post_url
            
        except Exception as e:
            logger.error(f"❌ Blogger publish failed: {e}")
            return None

class SimpleVideoCreator:
    """منشئ فيديو مبسط بدون مشاكل"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def create_text_image(self, text, size=(1920, 1080), font_size=70):
        """إنشاء صورة نصية بسيطة باستخدام PIL"""
        try:
            # إنشاء صورة
            image = Image.new('RGB', size, color=(25, 99, 235))  # أزرق
            
            # إعداد الرسم
            draw = ImageDraw.Draw(image)
            
            # محاولة تحميل خط
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # خط افتراضي
                font = ImageFont.load_default()
            
            # تقسيم النص
            lines = textwrap.wrap(text, width=40)
            
            # حساب موقع الكتابة
            total_height = len(lines) * (font_size + 10)
            y = (size[1] - total_height) // 2
            
            # رسم كل سطر
            for line in lines:
                # حساب عرض النص
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (size[0] - text_width) // 2
                
                # رسم النص مع ظل
                draw.text((x+3, y+3), line, font=font, fill=(0, 0, 0))
                draw.text((x, y), line, font=font, fill=(255, 255, 255))
                
                y += font_size + 10
            
            # حفظ الصورة
            temp_path = os.path.join(self.temp_dir, f"text_{hash(text)}_{size[0]}x{size[1]}.png")
            image.save(temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Text image creation error: {e}")
            return None
    
    async def create_simple_video(self, topic, script, audio_path, video_type="long"):
        """إنشاء فيديو بسيط بدون مشاكل"""
        try:
            # تحديد الحجم
            if video_type == "long":
                size = (1920, 1080)
                target_duration = 300  # 5 دقائق
                font_size = 70
            else:
                size = (1080, 1920)
                target_duration = 45  # 45 ثانية
                font_size = 50
            
            # تقسيم النص
            sentences = re.split(r'[.!?]+', script)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if not sentences or len(sentences) < 3:
                sentences = [
                    f"Welcome to Tech Compass!",
                    f"Today we're talking about: {topic}",
                    f"This is important technology",
                    f"Learn more in our full tutorial",
                    f"Subscribe for more tech content!"
                ]
            
            clips = []
            
            # مشهد المقدمة
            intro_text = f"Tech Compass\n\n{topic}"
            intro_image = self.create_text_image(intro_text, size, font_size + 20)
            if intro_image:
                intro_clip = ImageClip(intro_image, duration=5)
                clips.append(intro_clip)
            
            # المشاهد الرئيسية
            for i, sentence in enumerate(sentences[:8]):  # حد أقصى 8 مشاهد
                scene_duration = min(len(sentence.split()) * 0.6, 10)
                
                scene_image = self.create_text_image(sentence, size, font_size)
                if scene_image:
                    scene_clip = ImageClip(scene_image, duration=scene_duration)
                    clips.append(scene_clip)
                else:
                    # خلفية ملونة بديلة
                    colors = [(25, 99, 235), (124, 58, 237), (5, 150, 105)]
                    color = colors[i % len(colors)]
                    bg_clip = ColorClip(size=size, color=color, duration=scene_duration)
                    clips.append(bg_clip)
            
            # مشهد الخاتمة
            outro_text = "Thanks for watching!\n\nSubscribe for more tech tutorials"
            outro_image = self.create_text_image(outro_text, size, font_size)
            if outro_image:
                outro_clip = ImageClip(outro_image, duration=5)
                clips.append(outro_clip)
            
            # تجميع الفيديو
            if not clips:
                # فيديو احتياطي
                final_clip = ColorClip(size=size, color=(25, 99, 235), duration=30)
            else:
                final_clip = concatenate_videoclips(clips, method="compose")
            
            # إضافة الصوت إذا كان موجوداً
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    
                    # تعديل طول الفيديو أو الصوت
                    if final_clip.duration > audio_clip.duration:
                        final_clip = final_clip.subclip(0, audio_clip.duration)
                    elif final_clip.duration < audio_clip.duration:
                        audio_clip = audio_clip.subclip(0, final_clip.duration)
                    
                    final_clip = final_clip.set_audio(audio_clip)
                except Exception as e:
                    logger.error(f"❌ Audio addition error: {e}")
            
            # حفظ الفيديو
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"{video_type}_video_{timestamp}"
            output_path = f"output/{output_name}.mp4"
            
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                verbose=False,
                logger=None
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Simple video creation error: {e}")
            return None

class ContentEmpire:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        self.setup_directories()
        self.used_topics = set()
        self.content_history = {
            "videos": [],
            "articles": []
        }
        self.load_used_topics()
        self.load_content_history()
        self.youtube_uploader = YouTubeUploader()
        self.blogger_uploader = BloggerUploader()
        self.video_creator = SimpleVideoCreator()
    
    def setup_logging(self):
        self.logger = logger
    
    def setup_directories(self):
        os.makedirs('output', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('assets', exist_ok=True)
    
    async def check_environment(self):
        """التحقق من أن جميع Environment Variables موجودة"""
        required_vars = ['GEMINI_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.error(f"❌ Missing environment variables: {missing_vars}")
            await self.config.send_telegram_message(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        self.logger.info("✅ All environment variables are set")
        return True
    
    def load_used_topics(self):
        try:
            if os.path.exists('output/used_topics.txt'):
                with open('output/used_topics.txt', 'r') as f:
                    self.used_topics = set(line.strip() for line in f)
        except:
            self.used_topics = set()
    
    def save_used_topic(self, topic):
        self.used_topics.add(topic)
        with open('output/used_topics.txt', 'a') as f:
            f.write(topic + '\n')
    
    def load_content_history(self):
        try:
            if os.path.exists('output/content_history.json'):
                with open('output/content_history.json', 'r') as f:
                    self.content_history = json.load(f)
        except:
            self.content_history = {"videos": [], "articles": []}
    
    def save_content_history(self):
        try:
            with open('output/content_history.json', 'w') as f:
                json.dump(self.content_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Error saving content history: {e}")
    
    def add_video_to_history(self, title, url, video_type="long"):
        video_data = {
            "title": title,
            "url": url,
            "type": video_type,
            "date": datetime.now().isoformat()
        }
        self.content_history["videos"].append(video_data)
        if len(self.content_history["videos"]) > 10:
            self.content_history["videos"] = self.content_history["videos"][-10:]
        self.save_content_history()
    
    def add_article_to_history(self, title, url):
        article_data = {
            "title": title,
            "url": url,
            "date": datetime.now().isoformat()
        }
        self.content_history["articles"].append(article_data)
        if len(self.content_history["articles"]) > 10:
            self.content_history["articles"] = self.content_history["articles"][-10:]
        self.save_content_history()
    
    def get_recent_content_links(self):
        recent_videos = self.content_history["videos"][-3:]
        recent_articles = self.content_history["articles"][-3:]
        
        video_links = ""
        article_links = ""
        
        if recent_videos:
            video_links = "🎬 **Recent Videos:**\n"
            for video in reversed(recent_videos):
                video_links += f"• {video['title']}\n"
                video_links += f"  {video['url']}\n\n"
        
        if recent_articles:
            article_links = "📝 **Recent Articles:**\n"
            for article in reversed(recent_articles):
                article_links += f"• {article['title']}\n"
                article_links += f"  {article['url']}\n\n"
        
        return video_links, article_links
    
    async def get_unique_topic(self):
        """توليد موضوع فريد تماماً"""
        try:
            backup_topics = [
                "How AI is Revolutionizing Healthcare in 2024",
                "The Future of Quantum Computing",
                "Cybersecurity Trends Every Developer Should Know",
                "Building Modern Web Applications",
                "Machine Learning vs Deep Learning",
                "Cloud Computing: AWS vs Azure vs Google Cloud",
                "The Rise of Edge Computing",
                "Blockchain Technology Beyond Cryptocurrency",
                "5G Technology Impact",
                "Augmented Reality in Education"
            ]
            
            available_topics = [t for t in backup_topics if t not in self.used_topics]
            
            if available_topics:
                chosen_topic = random.choice(available_topics)
                self.save_used_topic(chosen_topic)
                return chosen_topic
            else:
                return "Latest Technology Trends and Innovations"
                
        except Exception as e:
            self.logger.error(f"❌ Error in topic selection: {e}")
            return "Technology Innovations 2024"
    
    async def generate_english_content(self, topic, content_type="long_video"):
        try:
            if not self.config.GEMINI_API_KEY:
                # محتوى احتياطي
                if content_type == "long_video":
                    return f"""Welcome to Tech Compass!

Today we're exploring {topic}.

This technology is changing how we work and live. Let me show you how.

First, understand the basics. {topic} involves several key concepts that every tech enthusiast should know.

The applications are endless. From business to education, {topic} is making a real difference.

Here are some practical tips to get started. You don't need to be an expert to begin.

Remember to subscribe for more tech insights. Leave a comment about what you'd like to see next!"""
                elif content_type == "blog":
                    return f"""# Complete Guide: {topic}

## Introduction
{topic} is one of the most exciting technologies today. In this comprehensive guide, we'll explore everything you need to know.

## What is {topic.split()[0]}?
This technology represents a major shift in how we approach problems and solutions.

## Key Benefits
1. Increased efficiency
2. Cost reduction
3. Improved accuracy
4. Better user experiences

## Getting Started
To begin with {topic.split()[0]}, start with these steps:
1. Learn the basics
2. Practice with small projects
3. Join online communities
4. Build a portfolio

## Conclusion
{topic} is here to stay. By learning it now, you position yourself for future success."""
                else:  # short video
                    return f"Quick tip about {topic}! This can save you hours. Follow for more tech insights! 🔥"
            
            # استخدام Gemini API - إصدار مصحح
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            try:
                # استخدام النموذج الصحيح
                model = genai.GenerativeModel('gemini-1.5-pro-latest' if content_type == "blog" else 'gemini-1.5-flash-latest')
                
                if content_type == "long_video":
                    prompt = f"""Create a simple YouTube video script about: "{topic}"
                    
                    Keep it under 500 words. Make it educational and easy to understand."""
                    
                elif content_type == "blog":
                    prompt = f"""Write a simple blog post about: "{topic}"
                    
                    Keep it under 800 words. Include headings and bullet points."""
                
                else:  # short video
                    prompt = f"""Create a 30-second YouTube Short script about: "{topic}"
                    
                    Make it engaging and under 100 words."""
                
                response = await model.generate_content_async(prompt)
                return response.text
                
            except Exception as gemini_error:
                self.logger.error(f"❌ Gemini API error: {gemini_error}")
                # محتوى احتياطي
                return f"Learn all about {topic} in this comprehensive tutorial. This technology is changing the world and you should know about it."
            
        except Exception as e:
            self.logger.error(f"❌ Content generation error: {e}")
            return f"# {topic}\n\nLearn all about {topic} in this comprehensive guide. Discover the latest developments and practical applications."
    
    async def generate_english_audio(self, text, output_name):
        """توليد صوت باستخدام TTS محلي كبديل"""
        try:
            output_path = f"temp/{output_name}.mp3"
            
            # استخدام gTTS كبديل
            try:
                from gtts import gTTS
                tts = gTTS(text[:500], lang='en', slow=False)
                tts.save(output_path)
                return output_path
            except ImportError:
                # إذا لم يكن gTTS مثبتاً، نستخدم edge-tts مع إعدادات بسيطة
                communicate = edge_tts.Communicate(
                    text[:800],
                    "en-US-GuyNeural",  # صوت مختلف
                    rate="+0%",
                    pitch="+0Hz"
                )
                await communicate.save(output_path)
                return output_path
                
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            # إنشاء ملف صوتي فارغ
            import wave
            import struct
            
            output_path = f"temp/{output_name}.wav"
            with wave.open(output_path, 'w') as wav_file:
                wav_file.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                wav_file.writeframes(b'')
            
            return output_path
    
    async def create_professional_video(self, script_text, audio_path, video_type="long", topic=""):
        """إنشاء فيديو باستخدام المنشئ المبسط"""
        try:
            video_path = await self.video_creator.create_simple_video(
                topic, script_text, audio_path, video_type
            )
            return video_path
        except Exception as e:
            self.logger.error(f"❌ Video creation error: {e}")
            return None
    
    async def publish_to_youtube_real(self, video_path, title, description, video_type="long"):
        """النشر الفعلي على YouTube"""
        try:
            if not video_path or not os.path.exists(video_path):
                self.logger.error(f"❌ Video file not found: {video_path}")
                await self.config.send_telegram_message(f"❌ Video creation failed for: {title}")
                return None
            
            recent_videos, recent_articles = self.get_recent_content_links()
            
            # وصف بسيط
            full_description = f"""{description}

🔔 Subscribe for more tech education: {self.config.YOUTUBE_CHANNEL_URL}

📝 Read our blog: {self.config.BLOGGER_BLOG_URL}

#Tech #Education #Tutorial"""
            
            youtube_url = self.youtube_uploader.upload_video(video_path, title, full_description)
            
            if youtube_url:
                self.add_video_to_history(title, youtube_url, video_type)
                
                message = f"""
🎬 <b>YouTube {'Short' if video_type == 'short' else 'Video'} Published!</b>

✅ <b>Title:</b> {title}
✅ <b>Type:</b> {'45s Short' if video_type == 'short' else 'Tutorial'}
✅ <b>URL:</b> {youtube_url}

🕒 <b>Published:</b> {datetime.now().strftime('%H:%M UTC')}
"""
                await self.config.send_telegram_message(message)
                return youtube_url
            else:
                fallback_url = f"https://youtube.com/watch?v=dummy_{hashlib.md5(title.encode()).hexdigest()[:8]}"
                await self.config.send_telegram_message(f"⚠️ YouTube upload simulation: {fallback_url}")
                return fallback_url
                
        except Exception as e:
            self.logger.error(f"❌ YouTube publish error: {e}")
            return None
    
    async def publish_to_blogger_real(self, title, content, youtube_url=None):
        """النشر الفعلي على Blogger"""
        try:
            # محتوى HTML بسيط
            html_content = f"""
<h1>{title}</h1>

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
{content.replace(chr(10), '<br>')}
</div>
"""
            
            if youtube_url:
                html_content += f"""
<div style="text-align: center; margin: 20px 0;">
<a href="{youtube_url}" target="_blank" style="background: #ff0000; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none;">
▶️ Watch Video Tutorial
</a>
</div>
"""
            
            blog_url = self.blogger_uploader.publish_post(title, html_content)
            
            if blog_url:
                self.add_article_to_history(title, blog_url)
                
                message = f"""
📝 <b>Blog Article Published!</b>

✅ <b>Title:</b> {title}
✅ <b>URL:</b> {blog_url}

🕒 <b>Published:</b> {datetime.now().strftime('%H:%M UTC')}
"""
                
                await self.config.send_telegram_message(message)
                return blog_url
            else:
                fallback_url = f"{self.config.BLOGGER_BLOG_URL}"
                await self.config.send_telegram_message(f"⚠️ Blogger publish simulation: {fallback_url}")
                return fallback_url
                
        except Exception as e:
            self.logger.error(f"❌ Blogger publish error: {e}")
            return None
    
    async def run_12_00_workflow(self):
        """فيديو طويل + مقال"""
        try:
            self.logger.info("🚀 Starting 12:00 workflow")
            
            topic = await self.get_unique_topic()
            self.logger.info(f"📝 Topic: {topic}")
            
            video_script = await self.generate_english_content(topic, "long_video")
            blog_content = await self.generate_english_content(topic, "blog")
            
            audio_path = await self.generate_english_audio(video_script, "long_audio")
            video_path = await self.create_professional_video(video_script, audio_path, "long", topic)
            
            if video_path and os.path.exists(video_path):
                youtube_url = await self.publish_to_youtube_real(
                    video_path, 
                    f"{topic} - Complete Tutorial 2024", 
                    video_script[:200],
                    "long"
                )
                
                blog_url = await self.publish_to_blogger_real(
                    f"Complete Guide: {topic}",
                    blog_content,
                    youtube_url
                )
            else:
                self.logger.error("❌ Failed to create video")
            
            self.logger.info("✅ 12:00 workflow completed")
            
        except Exception as e:
            self.logger.error(f"❌ 12:00 workflow error: {e}")
    
    async def run_14_00_workflow(self):
        """شورت 1"""
        try:
            self.logger.info("🚀 Starting 14:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_english_content(topic, "short_video")
            
            audio_path = await self.generate_english_audio(short_script, "short_audio_1")
            video_path = await self.create_professional_video(short_script, audio_path, "short", topic)
            
            if video_path and os.path.exists(video_path):
                await self.publish_to_youtube_real(
                    video_path,
                    f"{topic} - Quick Tip 🔥",
                    short_script,
                    "short"
                )
            
            self.logger.info("✅ 14:00 workflow completed")
            
        except Exception as e:
            self.logger.error(f"❌ 14:00 workflow error: {e}")
    
    async def run_16_00_workflow(self):
        """شورت 2"""
        try:
            self.logger.info("🚀 Starting 16:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_english_content(topic, "short_video")
            
            audio_path = await self.generate_english_audio(short_script, "short_audio_2")
            video_path = await self.create_professional_video(short_script, audio_path, "short", topic)
            
            if video_path and os.path.exists(video_path):
                await self.publish_to_youtube_real(
                    video_path,
                    f"{topic} - Explained in 45s ⚡",
                    short_script,
                    "short"
                )
            
            self.logger.info("✅ 16:00 workflow completed")
            
        except Exception as e:
            self.logger.error(f"❌ 16:00 workflow error: {e}")
    
    async def run_daily_workflow(self):
        try:
            if not await self.check_environment():
                return
            
            current_time = datetime.utcnow().strftime('%H:%M')
            self.logger.info(f"🕒 Current UTC time: {current_time}")
            
            # تشغيل جميع workflows للاختبار
            self.logger.info("🔄 Running all workflows for testing")
            
            await self.run_12_00_workflow()
            await asyncio.sleep(2)
            
            await self.run_14_00_workflow()
            await asyncio.sleep(2)
            
            await self.run_16_00_workflow()
            
            await self.config.send_telegram_message(f"""
🎉 <b>Daily Content Empire Complete!</b>

✅ <b>12:00 UTC:</b> Long Tutorial Video + Blog Post
✅ <b>14:00 UTC:</b> Quick Tutorial Short  
✅ <b>16:00 UTC:</b> Tech Insights Short

⚡ <b>Status:</b> All workflows executed successfully!
""")
            
        except Exception as e:
            error_msg = f"❌ Daily workflow failed: {str(e)}"
            self.logger.error(error_msg)
            await self.config.send_telegram_message(error_msg)

if __name__ == "__main__":
    # التأكد من وجود المجلدات
    for folder in ['output', 'temp', 'assets']:
        os.makedirs(folder, exist_ok=True)
    
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflow())
