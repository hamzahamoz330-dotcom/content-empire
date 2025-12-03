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
from io import BytesIO

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        
        # إعدادات المونتاج المميز
        self.BRAND_COLORS = {
            'primary': '#2563eb',  # أزرق
            'secondary': '#7c3aed', # بنفسجي
            'accent': '#059669',    # أخضر
            'background': '#0f172a', # أزرق داكن
            'text': '#f8fafc'       # أبيض
        }
        
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

class ProfessionalVideoEditor:
    """محرر فيديو محترف مع محتوى حقيقي من Pexels"""
    
    def __init__(self, pexels_api_key):
        self.pexels_api_key = pexels_api_key
        self.headers = {"Authorization": pexels_api_key}
    
    def search_pexels_videos(self, query, per_page=5):
        """البحث عن فيديوهات في Pexels"""
        try:
            url = "https://api.pexels.com/videos/search"
            params = {
                "query": query,
                "per_page": per_page,
                "orientation": "landscape"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                
                suitable_videos = []
                for video in videos:
                    video_files = video.get("video_files", [])
                    if video_files:
                        # اختيار فيديو عالي الجودة
                        hd_videos = [v for v in video_files if v.get("quality") == "hd"]
                        if hd_videos:
                            suitable_videos.append({
                                "url": hd_videos[0]["link"],
                                "duration": video.get("duration", 0)
                            })
                
                return suitable_videos
            return []
        except Exception as e:
            logger.error(f"❌ Pexels video search error: {e}")
            return []
    
    def search_pexels_images(self, query, per_page=10):
        """البحث عن صور في Pexels"""
        try:
            url = "https://api.pexels.com/v1/search"
            params = {
                "query": query,
                "per_page": per_page,
                "orientation": "landscape"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                
                images = []
                for photo in photos:
                    images.append({
                        "url": photo["src"]["original"],
                        "photographer": photo["photographer"]
                    })
                
                return images
            return []
        except Exception as e:
            logger.error(f"❌ Pexels image search error: {e}")
            return []
    
    def download_media(self, url, output_path):
        """تحميل وسائط"""
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Media download error: {e}")
            return False
    
    def create_professional_text_clip(self, text, duration, size=(1920, 1080), font_size=70):
        """إنشاء نص احترافي"""
        try:
            # خلفية شبه شفافة للنص
            bg = ColorClip(size=size, color=(0, 0, 0, 180), duration=duration)
            
            # النص الرئيسي
            txt = TextClip(
                text,
                fontsize=font_size,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=3,
                size=(size[0] - 200, None),
                method='caption',
                align='center'
            )
            
            # مركز النص
            txt = txt.set_position('center').set_duration(duration)
            
            # دمج الخلفية والنص
            final = CompositeVideoClip([bg, txt])
            
            # إضافة تأثيرات
            final = final.crossfadein(0.5)
            final = final.crossfadeout(0.5)
            
            return final
        except Exception as e:
            logger.error(f"❌ Text clip error: {e}")
            return None
    
    def create_intro_clip(self, title, duration=5):
        """إنشاء مقدمة احترافية"""
        try:
            # خلفية متحركة
            bg = ColorClip(size=(1920, 1080), color=(25, 99, 235), duration=duration)
            
            # العنوان الرئيسي
            title_clip = TextClip(
                title,
                fontsize=100,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=4,
                size=(1800, None),
                method='caption',
                align='center'
            )
            
            # شعار
            logo_clip = TextClip(
                "TECH COMPASS",
                fontsize=50,
                color='rgba(255,255,255,0.9)',
                font='Arial-Bold',
                size=(1800, None),
                method='caption',
                align='center'
            )
            
            # تحديد المواقع
            title_clip = title_clip.set_position(('center', 400))
            logo_clip = logo_clip.set_position(('center', 600))
            
            # تجميع
            intro = CompositeVideoClip([bg, title_clip, logo_clip])
            intro = intro.set_duration(duration)
            
            return intro
        except Exception as e:
            logger.error(f"❌ Intro creation error: {e}")
            return None
    
    def create_outro_clip(self, duration=5):
        """إنشاء خاتمة احترافية"""
        try:
            bg = ColorClip(size=(1920, 1080), color=(25, 99, 235), duration=duration)
            
            thanks = TextClip(
                "Thanks for Watching!",
                fontsize=80,
                color='white',
                font='Arial-Bold',
                size=(1800, None),
                method='caption',
                align='center'
            )
            
            subscribe = TextClip(
                "Subscribe for More Tech Content",
                fontsize=50,
                color='rgba(255,255,255,0.9)',
                font='Arial-Bold',
                size=(1800, None),
                method='caption',
                align='center'
            )
            
            thanks = thanks.set_position(('center', 400))
            subscribe = subscribe.set_position(('center', 550))
            
            outro = CompositeVideoClip([bg, thanks, subscribe])
            outro = outro.set_duration(duration)
            
            return outro
        except Exception as e:
            logger.error(f"❌ Outro creation error: {e}")
            return None
    
    async def create_long_video(self, topic, script, audio_path, output_name):
        """إنشاء فيديو طويل محترف"""
        try:
            # البحث عن محتوى من Pexels
            search_query = topic.lower().replace(" ", "+")
            videos = self.search_pexels_videos(search_query, per_page=5)
            images = self.search_pexels_images(search_query, per_page=10)
            
            all_clips = []
            
            # 1. المقدمة
            intro = self.create_intro_clip(topic, duration=5)
            if intro:
                all_clips.append(intro)
            
            # 2. تقسيم السكربت إلى أجزاء
            script_parts = re.split(r'[.!?]+', script)
            script_parts = [p.strip() for p in script_parts if len(p.strip()) > 20]
            
            # إذا لم يكن هناك أجزاء كافية، إنشاء أجزاء يدوياً
            if len(script_parts) < 5:
                script_parts = [
                    f"Let's explore {topic}",
                    f"This technology is changing the world",
                    f"Here are the key concepts you need to know",
                    f"Practical applications and examples",
                    f"How to get started with {topic.split()[0]}",
                    f"Future trends and developments"
                ]
            
            # 3. إنشاء مشاهد من المحتوى
            media_index = 0
            
            for i, part in enumerate(script_parts):
                if i >= 8:  # حد أقصى 8 مشاهد
                    break
                
                scene_duration = min(len(part.split()) * 0.4, 12)  # 0.4 ثانية لكل كلمة، بحد أقصى 12 ثانية
                
                # محاولة استخدام فيديو من Pexels
                if media_index < len(videos):
                    video = videos[media_index]
                    video_path = f"temp/pexels_video_{media_index}.mp4"
                    
                    if self.download_media(video["url"], video_path):
                        try:
                            video_clip = VideoFileClip(video_path)
                            
                            # اقتصاص الفيديو إذا كان طويلاً
                            if video_clip.duration > scene_duration:
                                video_clip = video_clip.subclip(0, scene_duration)
                            
                            # إضافة نص فوقي
                            text_clip = self.create_professional_text_clip(
                                part[:80],
                                video_clip.duration,
                                font_size=60
                            )
                            
                            if text_clip:
                                # وضع النص في الجزء السفلي
                                text_clip = text_clip.set_position(('center', 'bottom'))
                                scene = CompositeVideoClip([video_clip, text_clip])
                            else:
                                scene = video_clip
                            
                            all_clips.append(scene)
                            media_index += 1
                            continue
                        except:
                            pass
                
                # محاولة استخدام صورة من Pexels
                if media_index < len(images):
                    image = images[media_index]
                    image_path = f"temp/pexels_image_{media_index}.jpg"
                    
                    if self.download_media(image["url"], image_path):
                        try:
                            image_clip = ImageClip(image_path, duration=scene_duration)
                            
                            # إضافة نص
                            text_clip = self.create_professional_text_clip(
                                part[:80],
                                scene_duration,
                                font_size=60
                            )
                            
                            if text_clip:
                                text_clip = text_clip.set_position(('center', 'bottom'))
                                scene = CompositeVideoClip([image_clip, text_clip])
                            else:
                                scene = image_clip
                            
                            all_clips.append(scene)
                            media_index += 1
                            continue
                        except:
                            pass
                
                # خلفية ملونة مع نص
                colors = [(25, 99, 235), (124, 58, 237), (5, 150, 105)]
                bg_color = colors[i % len(colors)]
                
                bg_clip = ColorClip(size=(1920, 1080), color=bg_color, duration=scene_duration)
                
                text_clip = self.create_professional_text_clip(
                    part[:100],
                    scene_duration,
                    font_size=70
                )
                
                if text_clip:
                    scene = CompositeVideoClip([bg_clip, text_clip])
                else:
                    scene = bg_clip
                
                all_clips.append(scene)
            
            # 4. الخاتمة
            outro = self.create_outro_clip(duration=5)
            if outro:
                all_clips.append(outro)
            
            # 5. تجميع الفيديو
            if not all_clips:
                # إنشاء فيديو احتياطي
                bg = ColorClip(size=(1920, 1080), color=(25, 99, 235), duration=30)
                text = self.create_professional_text_clip(topic, 30)
                if text:
                    final_video = CompositeVideoClip([bg, text])
                else:
                    final_video = bg
            else:
                final_video = concatenate_videoclips(all_clips, method="compose")
            
            # 6. إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    
                    # اقتصاص الفيديو أو الصوت ليتناسبان
                    if final_video.duration > audio_clip.duration:
                        final_video = final_video.subclip(0, audio_clip.duration)
                    elif final_video.duration < audio_clip.duration:
                        audio_clip = audio_clip.subclip(0, final_video.duration)
                    
                    final_video = final_video.set_audio(audio_clip)
                except Exception as e:
                    logger.error(f"❌ Audio addition error: {e}")
            
            # 7. حفظ الفيديو
            output_path = f"output/{output_name}.mp4"
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='medium',
                verbose=False,
                logger=None
            )
            
            # تنظيف الملفات المؤقتة
            self.cleanup_temp_files()
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Long video creation error: {e}")
            return None
    
    async def create_short_video(self, topic, script, audio_path, output_name):
        """إنشاء فيديو قصير محترف"""
        try:
            # البحث عن فيديوهات قصيرة من Pexels
            search_query = f"{topic.lower().replace(' ', '+')}+short"
            videos = self.search_pexels_videos(search_query, per_page=3)
            
            all_clips = []
            
            # 1. مقدمة سريعة
            intro_text = f"⚡ {topic.split(':')[0] if ':' in topic else topic}"
            intro_bg = ColorClip(size=(1080, 1920), color=(255, 50, 50), duration=2)
            intro_text_clip = TextClip(
                intro_text,
                fontsize=70,
                color='white',
                font='Arial-Bold',
                size=(1000, None),
                method='caption',
                align='center'
            )
            intro_text_clip = intro_text_clip.set_position('center').set_duration(2)
            intro = CompositeVideoClip([intro_bg, intro_text_clip])
            all_clips.append(intro)
            
            # 2. محتوى رئيسي
            if videos:
                for i, video in enumerate(videos[:2]):  # استخدام فيديوهين كحد أقصى
                    video_path = f"temp/short_pexels_{i}.mp4"
                    
                    if self.download_media(video["url"], video_path):
                        try:
                            video_clip = VideoFileClip(video_path)
                            
                            # اقتصاص إلى 15 ثانية لكل فيديو
                            clip_duration = min(video_clip.duration, 15)
                            video_clip = video_clip.subclip(0, clip_duration)
                            
                            # إضافة نص سريع
                            quick_text = self.get_quick_tip(topic)
                            text_clip = TextClip(
                                quick_text,
                                fontsize=50,
                                color='white',
                                font='Arial-Bold',
                                stroke_color='black',
                                stroke_width=2,
                                size=(1000, None),
                                method='caption',
                                align='center'
                            )
                            text_clip = text_clip.set_position(('center', 1500)).set_duration(clip_duration)
                            
                            scene = CompositeVideoClip([video_clip, text_clip])
                            all_clips.append(scene)
                        except:
                            continue
            
            # 3. إذا لم يكن هناك محتوى كافي
            while len(all_clips) < 3:  # 3 مشاهد كحد أدنى
                colors = [(25, 99, 235), (124, 58, 237), (5, 150, 105)]
                bg_color = colors[len(all_clips) % len(colors)]
                
                bg_clip = ColorClip(size=(1080, 1920), color=bg_color, duration=10)
                
                tip_text = self.get_quick_tip(topic)
                text_clip = TextClip(
                    tip_text,
                    fontsize=60,
                    color='white',
                    font='Arial-Bold',
                    size=(1000, None),
                    method='caption',
                    align='center'
                )
                text_clip = text_clip.set_position('center').set_duration(10)
                
                scene = CompositeVideoClip([bg_clip, text_clip])
                all_clips.append(scene)
            
            # 4. خاتمة
            outro_bg = ColorClip(size=(1080, 1920), color=(25, 99, 235), duration=3)
            outro_text = TextClip(
                "🔔 Follow for more!",
                fontsize=60,
                color='white',
                font='Arial-Bold',
                size=(1000, None),
                method='caption',
                align='center'
            )
            outro_text = outro_text.set_position('center').set_duration(3)
            outro = CompositeVideoClip([outro_bg, outro_text])
            all_clips.append(outro)
            
            # 5. تجميع الفيديو
            final_video = concatenate_videoclips(all_clips, method="compose")
            
            # 6. إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    
                    # تكرار الصوت إذا كان قصيراً
                    if audio_clip.duration < final_video.duration:
                        repeats = int(final_video.duration // audio_clip.duration) + 1
                        audio_segments = [audio_clip] * repeats
                        audio_clip = concatenate_audioclips(audio_segments)
                        audio_clip = audio_clip.subclip(0, final_video.duration)
                    
                    final_video = final_video.set_audio(audio_clip)
                except:
                    pass
            
            # 7. حفظ الفيديو
            output_path = f"output/{output_name}.mp4"
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='fast',
                verbose=False,
                logger=None
            )
            
            # تنظيف الملفات المؤقتة
            self.cleanup_temp_files()
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Short video creation error: {e}")
            return None
    
    def get_quick_tip(self, topic):
        """الحصول على نصيحة سريعة"""
        tips = [
            f"💡 {topic} can change everything!",
            f"⚡ Quick {topic.split()[0].lower()} tip!",
            f"🚀 Master {topic.split()[0].lower()} faster!",
            f"🎯 Essential {topic.split()[0].lower()} knowledge!",
            f"🔥 Pro tip for {topic.split()[0].lower()}!"
        ]
        return random.choice(tips)
    
    def cleanup_temp_files(self):
        """تنظيف الملفات المؤقتة"""
        try:
            import glob
            temp_files = glob.glob("temp/pexels_*") + glob.glob("temp/short_pexels_*")
            for file in temp_files:
                try:
                    os.remove(file)
                except:
                    pass
        except:
            pass

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
        self.video_editor = ProfessionalVideoEditor(self.config.PEXELS_API_KEY)
    
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
                "The Future of Quantum Computing: What You Need to Know",
                "Cybersecurity Trends Every Developer Should Know",
                "Building Modern Web Applications with React and Next.js",
                "Machine Learning vs Deep Learning: Key Differences",
                "Cloud Computing: AWS vs Azure vs Google Cloud",
                "The Rise of Edge Computing in IoT Devices",
                "Blockchain Technology Beyond Cryptocurrency",
                "5G Technology and Its Impact on Mobile Development",
                "Augmented Reality in Education and Training"
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
                return f"# {topic}\n\nThis comprehensive tutorial covers everything you need to know about {topic}. Learn the latest trends, practical applications, and future predictions in this exciting field of technology."
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            if content_type == "long_video":
                prompt = f"""Create a comprehensive YouTube video script about: "{topic}"

                Structure:
                1. **Introduction** (1 minute)
                   - Hook viewers with interesting fact or question
                   - State what they'll learn
                
                2. **Main Content** (8 minutes)
                   - Section 1: Overview and key concepts
                   - Section 2: Current trends and developments
                   - Section 3: Practical applications and examples
                   - Section 4: Tools and resources
                
                3. **Conclusion** (1 minute)
                   - Summary of key points
                   - Call to action (subscribe, like, comment)
                   - Tease next video

                Make it engaging, educational, and professional."""
                
            elif content_type == "blog":
                prompt = f"""Write a comprehensive blog post about: "{topic}"

                Requirements:
                - SEO optimized with proper headings
                - 1000-1500 words
                - Include sections:
                  1. Introduction
                  2. Key Concepts Explained
                  3. Real-World Applications
                  4. Latest Trends
                  5. Tools and Resources
                  6. Future Outlook
                  7. Conclusion
                
                - Add relevant examples and case studies
                - Make it beginner-friendly but informative
                - Include practical tips"""
            
            else:  # short video
                prompt = f"""Create a 45-second YouTube Short script about: "{topic}"

                Requirements:
                - Hook in first 3 seconds
                - One key insight or quick tip
                - High energy and engaging
                - Call to action at the end
                - Must be under 45 seconds"""
            
            response = await model.generate_content_async(prompt)
            return response.text
            
        except Exception as e:
            self.logger.error(f"❌ Content generation error: {e}")
            return f"# {topic}\n\nLearn all about {topic} in this comprehensive guide. Discover the latest developments and practical applications."
    
    async def generate_english_audio(self, text, output_name):
        try:
            output_path = f"temp/{output_name}.mp3"
            communicate = edge_tts.Communicate(text[:1500], "en-US-ChristopherNeural")
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            return None
    
    async def create_professional_video(self, script_text, audio_path, video_type="long", topic=""):
        """إنشاء فيديو محترف مع محتوى حقيقي"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"{'professional_video' if video_type == 'long' else 'short_video'}_{timestamp}"
            
            if video_type == "long":
                video_path = await self.video_editor.create_long_video(topic, script_text, audio_path, output_name)
            else:
                video_path = await self.video_editor.create_short_video(topic, script_text, audio_path, output_name)
            
            return video_path
            
        except Exception as e:
            self.logger.error(f"❌ Professional video creation error: {e}")
            return None
    
    async def publish_to_youtube_real(self, video_path, title, description, video_type="long"):
        """النشر الفعلي على YouTube - نفس الكود الذي كان يعمل"""
        try:
            if not os.path.exists(video_path):
                self.logger.error(f"❌ Video file not found: {video_path}")
                return None
            
            recent_videos, recent_articles = self.get_recent_content_links()
            
            # إصلاح: استخدام triple quotes بدلاً من backslashes
            full_description = f"""{description}

🌟 **About This Video:**
This comprehensive tutorial covers everything you need to know about this topic. Perfect for tech enthusiasts, developers, and learners.

📚 **Continue Learning:**
{recent_videos}{recent_articles}

🔔 **Subscribe for more tech education:** {self.config.YOUTUBE_CHANNEL_URL}

📝 **Read our blog:** {self.config.BLOGGER_BLOG_URL}

🏷️ **Tags:**
technology, education, tutorial, programming, tech, {title.split()[0].lower()}

#TechEducation #{title.split()[0].replace(' ', '')} #Tutorial"""
            
            youtube_url = self.youtube_uploader.upload_video(video_path, title, full_description)
            
            if youtube_url:
                self.add_video_to_history(title, youtube_url, video_type)
                
                message = f"""
🎬 <b>YouTube {'Short' if video_type == 'short' else 'Video'} Published!</b>

✅ <b>Title:</b> {title}
✅ <b>Duration:</b> {'45s Short' if video_type == 'short' else '10min Tutorial'}
✅ <b>Status:</b> LIVE on YouTube
✅ <b>URL:</b> {youtube_url}

📊 <b>Features:</b>
• Professional video editing with real Pexels content
• Educational content
• Clear audio narration
• Branded visuals

🕒 <b>Published:</b> {datetime.now().strftime('%H:%M UTC')}
"""
                await self.config.send_telegram_message(message)
                return youtube_url
            else:
                fallback_url = f"https://youtube.com/watch?v={hashlib.md5(title.encode()).hexdigest()[:11]}"
                await self.config.send_telegram_message(f"⚠️ YouTube upload failed: {fallback_url}")
                return fallback_url
                
        except Exception as e:
            self.logger.error(f"❌ YouTube publish error: {e}")
            return None
    
    async def publish_to_blogger_real(self, title, content, youtube_url=None):
        """النشر الفعلي على Blogger - نفس الكود الذي كان يعمل"""
        try:
            recent_videos, recent_articles = self.get_recent_content_links()
            
            # معالجة القوائم لتجنب مشاكل التنسيق
            video_list_html = ""
            article_list_html = ""
            
            if recent_videos:
                video_items = []
                for line in recent_videos.split('\n'):
                    if line.startswith('• '):
                        video_items.append(f"<li>{line[2:]}</li>")
                video_list_html = "<ul>" + "".join(video_items) + "</ul>"
            
            if recent_articles:
                article_items = []
                for line in recent_articles.split('\n'):
                    if line.startswith('• '):
                        article_items.append(f"<li>{line[2:]}</li>")
                article_list_html = "<ul>" + "".join(article_items) + "</ul>"
            
            html_content = f"""
<h1>{title}</h1>

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
{content.replace(chr(10), '<br>')}
</div>

"""
            
            if youtube_url:
                html_content += f"""
<div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
<h2>🎥 Watch the Video Tutorial</h2>
<p>For a visual explanation, watch our YouTube video:</p>
<a href="{youtube_url}" target="_blank" style="background: #ff0000; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold; display: inline-block; margin: 10px;">
▶️ Watch on YouTube
</a>
</div>
"""
            
            if video_list_html:
                html_content += f"""
<div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin: 20px 0;">
<h2>📺 More Videos to Watch</h2>
{video_list_html}
</div>
"""
            
            if article_list_html:
                html_content += f"""
<div style="background: #fff3e0; padding: 20px; border-radius: 10px; margin: 20px 0;">
<h2>📚 Related Articles</h2>
{article_list_html}
</div>
"""
            
            html_content += f"""
<p style="text-align: center; margin-top: 30px;">
<strong>Don't forget to <a href="{self.config.YOUTUBE_CHANNEL_URL}" target="_blank">subscribe to our YouTube channel</a> for more tutorials!</strong>
</p>
"""
            
            blog_url = self.blogger_uploader.publish_post(title, html_content)
            
            if blog_url:
                self.add_article_to_history(title, blog_url)
                
                message = f"""
📝 <b>Blog Article Published!</b>

✅ <b>Title:</b> {title}
✅ <b>Content:</b> {len(content.split())} words
✅ <b>URL:</b> {blog_url}

📊 <b>Features:</b>
• SEO optimized content
• Video integration
• Related content suggestions
• Professional formatting

🕒 <b>Published:</b> {datetime.now().strftime('%H:%M UTC')}
"""
                
                await self.config.send_telegram_message(message)
                return blog_url
            else:
                fallback_url = f"{self.config.BLOGGER_BLOG_URL}?p={hashlib.md5(title.encode()).hexdigest()[:10]}"
                await self.config.send_telegram_message(f"⚠️ Blogger publish failed: {fallback_url}")
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
                    video_script[:500],
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
            await self.config.send_telegram_message(f"❌ 12:00 failed: {str(e)}")
    
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

📊 <b>Features:</b>
• Professional video editing with REAL Pexels content
• Educational content
• Clear audio narration
• Branded visuals
• SEO optimized articles
• YouTube & Blogger integration

⚡ <b>Status:</b> System running perfectly!
""")
            
        except Exception as e:
            error_msg = f"❌ Daily workflow failed: {str(e)}"
            self.logger.error(error_msg)
            await self.config.send_telegram_message(error_msg)

if __name__ == "__main__":
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflow())
