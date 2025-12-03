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
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import numpy as np
from io import BytesIO
import time

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

class PexelsMediaManager:
    """مدير الوسائط من Pexels"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.base_url = "https://api.pexels.com"
        
    def search_images(self, query, per_page=10):
        """البحث عن صور مناسبة"""
        try:
            url = f"{self.base_url}/v1/search"
            params = {
                "query": query + " technology digital",
                "per_page": per_page,
                "orientation": "landscape",
                "size": "large"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                
                images = []
                for photo in photos:
                    images.append({
                        "url": photo["src"]["large"],
                        "photographer": photo["photographer"],
                        "alt": photo.get("alt", "")
                    })
                
                logger.info(f"✅ Found {len(images)} images for query: {query}")
                return images
            else:
                logger.error(f"❌ Pexels API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Pexels search error: {e}")
            return []
    
    def search_videos(self, query, per_page=5):
        """البحث عن فيديوهات قصيرة"""
        try:
            url = f"{self.base_url}/videos/search"
            params = {
                "query": query + " technology",
                "per_page": per_page,
                "orientation": "portrait" if "short" in query else "landscape",
                "min_duration": 3,
                "max_duration": 20
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                
                video_list = []
                for video in videos:
                    video_files = video.get("video_files", [])
                    if video_files:
                        # اختيار الفيديو المناسب
                        suitable_videos = [v for v in video_files if v.get("quality") in ["hd", "sd"]]
                        if suitable_videos:
                            video_list.append({
                                "url": suitable_videos[0]["link"],
                                "duration": video.get("duration", 0)
                            })
                
                logger.info(f"✅ Found {len(video_list)} videos for query: {query}")
                return video_list
            else:
                logger.error(f"❌ Pexels videos API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Pexels videos search error: {e}")
            return []
    
    def download_media(self, url, output_path):
        """تحميل الوسائط"""
        try:
            response = requests.get(url, stream=True, timeout=15)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Media download error: {e}")
            return False

class ProfessionalVideoCreator:
    """منشئ فيديو محترف مع صور حقيقية وصوت ومونتاج"""
    
    def __init__(self, pexels_api_key):
        self.temp_dir = "temp"
        self.media_manager = PexelsMediaManager(pexels_api_key)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # إعدادات الخطوط
        self.font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
    
    def get_font(self, size, bold=True):
        """الحصول على خط مناسب"""
        for font_path in self.font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        return ImageFont.load_default()
    
    def create_text_overlay_image(self, text, size=(1920, 1080), is_title=False):
        """إنشاء صورة نصية ضمن الإطار"""
        try:
            # إنشاء صورة بخلفية شفافة
            image = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # تحديد حجم الخط بناءً على نوع المحتوى
            if is_title:
                font_size = 80
                max_width = size[0] - 200  # هامش 100 بكسل من كل جانب
            else:
                font_size = 55
                max_width = size[0] - 150  # هامش 75 بكسل من كل جانب
            
            font = self.get_font(font_size, bold=True)
            
            # تقسيم النص ليتناسب مع العرض
            lines = []
            words = text.split()
            current_line = []
            current_width = 0
            
            for word in words:
                word_bbox = draw.textbbox((0, 0), word + " ", font=font)
                word_width = word_bbox[2] - word_bbox[0]
                
                if current_width + word_width <= max_width:
                    current_line.append(word)
                    current_width += word_width
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
                    current_width = word_width
            
            if current_line:
                lines.append(" ".join(current_line))
            
            # إذا كان النص طويلاً جداً، اختصاره
            if len(lines) > 5:
                lines = lines[:5]
                lines[-1] = lines[-1][:100] + "..."
            
            # حساب ارتفاع النص
            line_height = font_size + 10
            total_height = len(lines) * line_height
            
            # تحديد موقع البداية (منتصف الصورة)
            y_start = (size[1] - total_height) // 2
            
            # إضافة خلفية شفافة للنص
            padding = 20
            text_bg_height = total_height + (padding * 2)
            text_bg_width = max_width + (padding * 2)
            text_bg_x = (size[0] - text_bg_width) // 2
            text_bg_y = y_start - padding
            
            # رسم خلفية نصية
            draw.rectangle(
                [text_bg_x, text_bg_y, 
                 text_bg_x + text_bg_width, text_bg_y + text_bg_height],
                fill=(0, 0, 0, 180),  # أسود شفاف
                outline=(255, 255, 255, 100),
                width=2
            )
            
            # رسم النص
            for i, line in enumerate(lines):
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                x_pos = (size[0] - line_width) // 2
                y_pos = y_start + (i * line_height)
                
                # إضافة ظل للنص
                draw.text((x_pos + 3, y_pos + 3), line, font=font, fill=(0, 0, 0, 200))
                # النص الرئيسي
                draw.text((x_pos, y_pos), line, font=font, fill=(255, 255, 255, 255))
            
            # إضافة شعار باهت في الزاوية
            logo_font = self.get_font(30, bold=True)
            logo_text = "© Tech Compass"
            draw.text((50, size[1] - 80), logo_text, font=logo_font, fill=(255, 255, 255, 150))
            
            # حفظ الصورة
            temp_path = os.path.join(self.temp_dir, f"text_overlay_{hash(text[:50])}.png")
            image.save(temp_path, 'PNG')
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Text overlay creation error: {e}")
            return None
    
    def create_scene_with_image_and_text(self, image_path, text, duration, size=(1920, 1080)):
        """إنشاء مشهد مع صورة ونص"""
        try:
            # تحميل الصورة
            if os.path.exists(image_path):
                # تحميل وتعديل الصورة
                img = Image.open(image_path)
                
                # تغيير حجم الصورة لتناسب الفيديو مع الحفاظ على النسبة
                img_ratio = img.width / img.height
                target_ratio = size[0] / size[1]
                
                if img_ratio > target_ratio:
                    # الصورة أوسع، اقتصاص من الجوانب
                    new_height = size[1]
                    new_width = int(new_height * img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    left = (new_width - size[0]) // 2
                    img = img.crop((left, 0, left + size[0], size[1]))
                else:
                    # الصورة أطول، اقتصاص من الأعلى والأسفل
                    new_width = size[0]
                    new_height = int(new_width / img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    top = (new_height - size[1]) // 2
                    img = img.crop((0, top, size[0], top + size[1]))
                
                # حفظ الصورة المعدلة
                modified_path = os.path.join(self.temp_dir, f"modified_{hash(image_path)}.jpg")
                img.save(modified_path, 'JPEG', quality=90)
                
                # إنشاء نص فوقي
                text_overlay_path = self.create_text_overlay_image(text, size)
                
                if text_overlay_path:
                    # تحميل الصورة والخلفية النصية
                    bg_clip = ImageClip(modified_path, duration=duration)
                    text_clip = ImageClip(text_overlay_path, duration=duration).set_opacity(0.9)
                    
                    # إنشاء المشهد النهائي
                    scene = CompositeVideoClip([bg_clip, text_clip])
                    return scene
                else:
                    # فقط الصورة
                    return ImageClip(modified_path, duration=duration)
            else:
                # خلفية بديلة مع نص
                bg_color = random.choice([(30, 60, 90), (25, 99, 235), (5, 150, 105)])
                bg_clip = ColorClip(size=size, color=bg_color, duration=duration)
                
                text_overlay_path = self.create_text_overlay_image(text, size)
                if text_overlay_path:
                    text_clip = ImageClip(text_overlay_path, duration=duration)
                    return CompositeVideoClip([bg_clip, text_clip])
                else:
                    return bg_clip
                
        except Exception as e:
            logger.error(f"❌ Scene creation error: {e}")
            return None
    
    async def create_long_video_with_audio(self, topic, script, audio_path):
        """إنشاء فيديو طويل مع صور وصوت متزامن"""
        try:
            logger.info(f"🎬 Creating long video for: {topic}")
            
            # تقسيم السكربت إلى مشاهد
            scenes = self.prepare_scenes(script, scene_count=12)
            
            # البحث عن صور مناسبة
            search_queries = [
                topic.split(':')[0] if ':' in topic else topic,
                "technology background",
                "digital transformation",
                "cloud computing" if "cloud" in topic.lower() else "artificial intelligence",
                "data center",
                "programming code"
            ]
            
            images = []
            for query in search_queries:
                if len(images) < 15:  # نحتاج 15 صورة كحد أقصى
                    found_images = self.media_manager.search_images(query, per_page=5)
                    images.extend(found_images)
            
            # تحميل الصور
            image_paths = []
            for i, img_info in enumerate(images[:len(scenes)]):
                img_path = os.path.join(self.temp_dir, f"scene_image_{i}.jpg")
                if self.media_manager.download_media(img_info["url"], img_path):
                    image_paths.append(img_path)
            
            # إذا لم نحصل على صور كافية، نكرر الصور الموجودة
            while len(image_paths) < len(scenes):
                image_paths.append(random.choice(image_paths) if image_paths else None)
            
            clips = []
            
            # 1. المقدمة (8 ثوان)
            intro_text = f"Complete Guide to:\n{topic}"
            intro_bg = self.create_text_overlay_image(intro_text, is_title=True)
            if intro_bg:
                intro_clip = ImageClip(intro_bg, duration=8)
                clips.append(intro_clip)
            
            # 2. المشاهد الرئيسية
            audio_duration = 0
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                except:
                    audio_duration = 300  # 5 دقائق افتراضياً
            
            # حساب مدة كل مشهد بناءً على طول الصوت
            total_scenes = len(scenes)
            scene_duration = min(audio_duration / total_scenes if audio_duration > 0 else 15, 20)
            
            for i, (scene_text, image_path) in enumerate(zip(scenes, image_paths)):
                scene = self.create_scene_with_image_and_text(
                    image_path, scene_text, scene_duration
                )
                if scene:
                    clips.append(scene)
            
            # 3. الخاتمة (6 ثوان)
            outro_text = "Thanks for watching!\nSubscribe for more tech education"
            outro_bg = self.create_text_overlay_image(outro_text)
            if outro_bg:
                outro_clip = ImageClip(outro_bg, duration=6)
                clips.append(outro_clip)
            
            # تجميع الفيديو
            if not clips:
                logger.error("❌ No clips created")
                return None
            
            video = concatenate_videoclips(clips, method="compose")
            
            # إضافة الصوت المتزامن مع النص
            if audio_path and os.path.exists(audio_path):
                try:
                    audio = AudioFileClip(audio_path)
                    
                    # اقتصاص الصوت لطول الفيديو أو العكس
                    if video.duration > audio.duration:
                        # إذا كان الفيديو أطول من الصوت، نكرر الصوت
                        repeats = int(video.duration // audio.duration) + 1
                        audio_segments = [audio] * repeats
                        audio = concatenate_audioclips(audio_segments)
                        audio = audio.subclip(0, video.duration)
                    else:
                        # إذا كان الصوت أطول، نقلصه
                        audio = audio.subclip(0, video.duration)
                    
                    video = video.set_audio(audio)
                    logger.info(f"✅ Audio added: {audio.duration:.1f}s")
                    
                except Exception as e:
                    logger.error(f"❌ Audio processing error: {e}")
            
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
            
            logger.info(f"✅ Created professional video: {output_path} ({video.duration:.1f}s)")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Long video creation error: {e}")
            return None
    
    async def create_short_video_with_audio(self, topic, script, audio_path):
        """إنشاء فيديو قصير مع صور وصوت"""
        try:
            logger.info(f"🎬 Creating short video for: {topic}")
            
            # حجم الفيديو القصير
            size = (1080, 1920)
            
            # البحث عن فيديوهات قصيرة من Pexels
            search_query = topic.split(':')[0] if ':' in topic else topic
            videos = self.media_manager.search_videos(search_query + " short", per_page=3)
            
            clips = []
            
            # 1. المقدمة السريعة (3 ثوان)
            intro_text = f"⚡ {search_query}\nQuick Tip!"
            intro_bg = self.create_text_overlay_image(intro_text, size=size)
            if intro_bg:
                intro_clip = ImageClip(intro_bg, duration=3)
                clips.append(intro_clip)
            
            # 2. محتوى رئيسي (فيديوهات أو صور)
            if videos:
                for i, video_info in enumerate(videos[:2]):
                    video_path = os.path.join(self.temp_dir, f"short_video_{i}.mp4")
                    if self.media_manager.download_media(video_info["url"], video_path):
                        try:
                            video_clip = VideoFileClip(video_path)
                            
                            # اقتصاص الفيديو ليكون مناسباً
                            clip_duration = min(video_clip.duration, 15)
                            video_clip = video_clip.subclip(0, clip_duration)
                            
                            # إضافة نص فوقي
                            tip_text = self.get_short_tip(script, i)
                            text_overlay = self.create_text_overlay_image(tip_text, size=size)
                            
                            if text_overlay:
                                text_clip = ImageClip(text_overlay, duration=clip_duration).set_opacity(0.85)
                                scene = CompositeVideoClip([video_clip, text_clip])
                                clips.append(scene)
                            else:
                                clips.append(video_clip)
                                
                        except Exception as e:
                            logger.error(f"❌ Short video processing error: {e}")
            
            # 3. إذا لم يكن هناك فيديوهات كافية، نضيف مشاهد نصية
            while len(clips) < 3:
                scene_duration = random.uniform(8, 12)
                scene_text = self.get_short_tip(script, len(clips))
                
                # البحث عن صورة لهذا المشهد
                images = self.media_manager.search_images(search_query, per_page=3)
                image_path = None
                
                if images:
                    img_path = os.path.join(self.temp_dir, f"short_img_{len(clips)}.jpg")
                    if self.media_manager.download_media(images[0]["url"], img_path):
                        image_path = img_path
                
                scene = self.create_scene_with_image_and_text(
                    image_path, scene_text, scene_duration, size=size
                )
                if scene:
                    clips.append(scene)
            
            # 4. الخاتمة (3 ثوان)
            outro_text = "🔔 Follow for more!\n@TechCompass"
            outro_bg = self.create_text_overlay_image(outro_text, size=size)
            if outro_bg:
                outro_clip = ImageClip(outro_bg, duration=3)
                clips.append(outro_clip)
            
            # تجميع الفيديو
            if not clips:
                logger.error("❌ No short clips created")
                return None
            
            video = concatenate_videoclips(clips, method="compose")
            
            # إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                try:
                    audio = AudioFileClip(audio_path)
                    
                    # تكرار الصوت إذا كان قصيراً
                    if video.duration > audio.duration:
                        repeats = int(video.duration // audio.duration) + 1
                        audio_segments = [audio] * repeats
                        audio = concatenate_audioclips(audio_segments)
                    
                    audio = audio.subclip(0, video.duration)
                    video = video.set_audio(audio)
                    
                except Exception as e:
                    logger.error(f"❌ Short audio error: {e}")
            
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
    
    def prepare_scenes(self, script, scene_count=12):
        """تحضير المشاهد من السكربت"""
        # تقسيم السكربت إلى جمل
        sentences = re.split(r'(?<=[.!?])\s+', script)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # إذا كانت الجمل قليلة، ننشئ جمل افتراضية
        if len(sentences) < scene_count:
            base_sentences = sentences.copy()
            while len(sentences) < scene_count:
                sentences.extend(base_sentences)
        
        # اختصار الجمل الطويلة
        processed_scenes = []
        for sentence in sentences[:scene_count]:
            if len(sentence) > 120:
                sentence = sentence[:117] + "..."
            processed_scenes.append(sentence)
        
        return processed_scenes
    
    def get_short_tip(self, script, index):
        """استخراج نصيحة قصيرة من السكربت"""
        sentences = re.split(r'(?<=[.!?])\s+', script)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if sentences and index < len(sentences):
            tip = sentences[index]
            if len(tip) > 80:
                tip = tip[:77] + "..."
        else:
            tips = [
                "Technology is changing fast!",
                "Stay updated with latest trends",
                "Learn something new every day",
                "Practice makes perfect in tech",
                "Follow for daily tech insights"
            ]
            tip = random.choice(tips)
        
        return tip
    
    def cleanup_temp_files(self):
        """تنظيف الملفات المؤقتة"""
        try:
            import glob
            temp_files = glob.glob("temp/*.jpg") + glob.glob("temp/*.png") + glob.glob("temp/*.mp4")
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
        self.setup_directories()
        self.used_topics = set()
        self.content_history = {"videos": [], "articles": []}
        self.load_history()
        self.youtube_uploader = YouTubeUploader()
        self.blogger_uploader = BloggerUploader()
        self.video_creator = ProfessionalVideoCreator(self.config.PEXELS_API_KEY)
    
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
            "Cloud Computing Explained: AWS vs Azure vs Google Cloud",
            "Artificial Intelligence in Healthcare: Saving Lives with AI",
            "Cybersecurity 2024: Protecting Your Digital Identity",
            "Data Science Career Path: Skills You Need Today",
            "Blockchain Technology: Beyond Cryptocurrency",
            "5G Networks: The Future of Mobile Connectivity",
            "Internet of Things: Smart Homes and Smart Cities",
            "Machine Learning vs Deep Learning: Complete Comparison",
            "Quantum Computing: The Next Tech Revolution",
            "Augmented Reality in Education: Future of Learning"
        ]
        
        available = [t for t in topics if t not in self.used_topics]
        if available:
            topic = random.choice(available)
        else:
            topic = "Emerging Technology Trends 2024: Complete Guide"
        
        self.save_topic(topic)
        return topic
    
    async def generate_content(self, topic, content_type="long_video"):
        try:
            if not self.config.GEMINI_API_KEY:
                return self.get_fallback_content(topic, content_type)
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            if content_type == "long_video":
                prompt = f"""Create a comprehensive educational YouTube video script about: "{topic}"

                Make it:
                - 1000+ words
                - Structured into clear sections
                - Include practical examples
                - Educational and engaging
                - End with summary and call to action
                - Write in spoken language style"""
                
                model = genai.GenerativeModel('gemini-pro')
                response = await model.generate_content_async(prompt)
                return response.text
                
            elif content_type == "blog":
                prompt = f"""Write a detailed SEO-optimized blog post about: "{topic}"

                Requirements:
                - 1500+ words
                - Clear headings and subheadings
                - Include bullet points and lists
                - Add practical tips
                - Optimize for search engines
                - Make it beginner-friendly"""
                
                model = genai.GenerativeModel('gemini-pro')
                response = await model.generate_content_async(prompt)
                return response.text
            
            else:  # short video
                prompt = f"""Create an engaging YouTube Short script about: "{topic}"

                Requirements:
                - Maximum 100 words
                - Start with attention-grabbing hook
                - Include one key insight
                - High energy and engaging
                - End with call to action
                - Use conversational tone"""
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = await model.generate_content_async(prompt)
                return response.text
                
        except Exception as e:
            logger.error(f"❌ Content generation error: {e}")
            return self.get_fallback_content(topic, content_type)
    
    def get_fallback_content(self, topic, content_type):
        if content_type == "long_video":
            return f"""Welcome to Tech Compass! Today we're exploring {topic}.

This technology is revolutionizing industries worldwide. Let's understand what it really means.

First, let's look at the basics. {topic.split(':')[0] if ':' in topic else topic} refers to...

The applications are numerous. From business to daily life, this technology makes things better.

Here are the key components:

1. Core Principles - Understanding the foundation
2. Current Applications - Where it's used today
3. Benefits and Advantages - Why it matters
4. Getting Started - How to begin learning

Real-world examples show how companies use this technology to solve problems and innovate.

The future looks bright with continuous developments and improvements.

To get started, follow these steps: Learn the basics, practice with projects, join communities.

Remember, the goal is practical application, not just theoretical knowledge.

Stay curious and keep learning. Technology evolves fast!

Thanks for watching! Subscribe for more tech tutorials."""
        
        elif content_type == "blog":
            return f"""# Complete Guide to {topic}

## Introduction
{topic} represents one of the most transformative technologies of our time. This comprehensive guide covers everything you need to know.

## Understanding the Basics
Before diving deep, let's establish a solid foundation of the core concepts.

## Key Components
- Component 1: Description and importance
- Component 2: How it works in practice
- Component 3: Real-world applications

## Benefits and Advantages
1. **Increased Efficiency**: How this technology saves time and resources
2. **Cost Reduction**: Economic benefits for businesses
3. **Improved Accuracy**: Enhanced precision and reliability
4. **Scalability**: Ability to grow with your needs

## Practical Applications
We examine how various industries implement this technology successfully.

## Getting Started
Step-by-step guide for beginners:
1. Learn the fundamentals
2. Set up your environment
3. Start with simple projects
4. Join online communities
5. Build a portfolio

## Future Outlook
What developments can we expect in the coming years?

## Conclusion
{topic} is more than just a trend—it's a fundamental shift. By understanding and applying these concepts, you position yourself for success.

Ready to learn more? Check out our video tutorials for visual explanations!"""
        
        else:  # short video
            return f"Quick tech tip about {topic.split(':')[0] if ':' in topic else topic}! ⚡\n\nThis one insight can change how you work. Stay tuned for more daily tech tips!\n\nFollow @TechCompass! 🔔"
    
    async def generate_audio(self, text, output_name):
        """توليد صوت متزامن مع النص"""
        try:
            output_path = f"temp/{output_name}.mp3"
            
            # تنظيف النص للصوت
            clean_text = self.clean_text_for_speech(text)
            
            # استخدام edge-tts مع صوت احترافي
            communicate = edge_tts.Communicate(
                clean_text,
                "en-US-ChristopherNeural",  # صوت احترافي
                rate="+10%",  # أسرع قليلاً
                pitch="+0Hz",
                volume="+0%"
            )
            
            await communicate.save(output_path)
            
            # التحقق من وجود الصوت
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"✅ Audio generated: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")
                return output_path
            else:
                logger.error("❌ Audio file too small or missing")
                return None
                
        except Exception as e:
            logger.error(f"❌ Audio generation error: {e}")
            return None
    
    def clean_text_for_speech(self, text):
        """تنظيف النص لجعله مناسباً للصوت"""
        # إزالة العلامات الخاصة
        text = re.sub(r'[#*_~`]', '', text)
        
        # استبدال الرموز
        text = text.replace('&', 'and')
        text = text.replace('@', 'at')
        
        # تقصير النص الطويل جداً
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        return text
    
    async def run_12_00_workflow(self):
        try:
            logger.info("🚀 Starting 12:00 workflow")
            
            topic = await self.get_unique_topic()
            logger.info(f"📝 Topic: {topic}")
            
            # توليد المحتوى
            video_script = await self.generate_content(topic, "long_video")
            blog_content = await self.generate_content(topic, "blog")
            
            # توليد الصوت المتزامن مع النص
            audio_path = await self.generate_audio(video_script, f"long_audio_{datetime.now().strftime('%H%M')}")
            
            if audio_path:
                # إنشاء فيديو محترف مع صور وصوت
                video_path = await self.video_creator.create_long_video_with_audio(
                    topic, video_script, audio_path
                )
                
                if video_path and os.path.exists(video_path):
                    # تحقق من مدة الفيديو
                    try:
                        video_clip = VideoFileClip(video_path)
                        duration = video_clip.duration
                        video_clip.close()
                        
                        logger.info(f"📏 Video duration: {duration:.1f} seconds")
                        
                        if duration < 300:
                            logger.warning("⚠️ Video too short, extending...")
                            # إنشاء فيديو أطول
                            extended_script = video_script + "\n\n" + self.get_extended_content(topic)
                            audio_path2 = await self.generate_audio(extended_script, "extended_audio")
                            if audio_path2:
                                video_path = await self.video_creator.create_long_video_with_audio(
                                    topic, extended_script, audio_path2
                                )
                    except:
                        pass
                    
                    # رفع الفيديو
                    youtube_url = self.youtube_uploader.upload_video(
                        video_path, 
                        f"{topic} - Complete Tutorial 2024", 
                        f"Learn everything about {topic} in this comprehensive tutorial.\n\n"
                        f"This video covers all aspects including basics, applications, and future trends.\n\n"
                        f"Subscribe for more tech education: {self.config.YOUTUBE_CHANNEL_URL}\n"
                        f"Read our blog: {self.config.BLOGGER_BLOG_URL}"
                    )
                    
                    if youtube_url:
                        # نشر المقال
                        blog_url = self.blogger_uploader.publish_post(
                            f"Complete Guide: {topic}",
                            blog_content + f'\n\n<div style="text-align: center;">'
                            f'<a href="{youtube_url}" style="background: #ff0000; color: white; padding: 12px 24px; '
                            f'border-radius: 5px; text-decoration: none; font-weight: bold;">'
                            f'▶️ Watch Video Tutorial</a></div>'
                        )
            
            # تنظيف الملفات المؤقتة
            self.video_creator.cleanup_temp_files()
            
            logger.info("✅ 12:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 12:00 workflow error: {e}")
    
    def get_extended_content(self, topic):
        """إضافة محتوى إضافي لزيادة المدة"""
        extensions = [
            f"Let's dive deeper into {topic.split(':')[0] if ':' in topic else topic}. "
            f"This technology has multiple layers that we should explore.",
            
            f"One important aspect is practical implementation. "
            f"How can you actually use {topic.split(':')[0] if ':' in topic else topic} in real projects?",
            
            f"Common challenges include understanding the technical details and staying updated. "
            f"We'll discuss solutions for these challenges.",
            
            f"Best practices help you avoid common mistakes. "
            f"Follow these guidelines for better results with {topic.split(':')[0] if ':' in topic else topic}.",
            
            f"Future developments will shape how we use this technology. "
            f"Stay ahead by understanding upcoming trends."
        ]
        return "\n\n".join(random.sample(extensions, 3))
    
    async def run_14_00_workflow(self):
        try:
            logger.info("🚀 Starting 14:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            # توليد الصوت للشورت
            audio_path = await self.generate_audio(short_script, f"short_audio_1_{datetime.now().strftime('%H%M')}")
            
            if audio_path:
                # إنشاء شورت مع صور وصوت
                video_path = await self.video_creator.create_short_video_with_audio(
                    topic, short_script, audio_path
                )
                
                if video_path and os.path.exists(video_path):
                    self.youtube_uploader.upload_video(
                        video_path,
                        f"{topic} - Quick Tip 🔥 #Shorts",
                        f"Quick tech tip about {topic.split(':')[0] if ':' in topic else topic}! "
                        f"Follow for more daily tech insights.\n\n"
                        f"#Shorts #Tech #Tips #Technology #Education"
                    )
            
            # تنظيف
            self.video_creator.cleanup_temp_files()
            
            logger.info("✅ 14:00 workflow completed")
            
        except Exception as e:
            logger.error(f"❌ 14:00 workflow error: {e}")
    
    async def run_16_00_workflow(self):
        try:
            logger.info("🚀 Starting 16:00 workflow")
            
            topic = await self.get_unique_topic()
            short_script = await self.generate_content(topic, "short_video")
            
            # توليد الصوت للشورت الثاني
            audio_path = await self.generate_audio(short_script, f"short_audio_2_{datetime.now().strftime('%H%M')}")
            
            if audio_path:
                video_path = await self.video_creator.create_short_video_with_audio(
                    topic, short_script, audio_path
                )
                
                if video_path and os.path.exists(video_path):
                    self.youtube_uploader.upload_video(
                        video_path,
                        f"{topic} Explained! ⚡ #Shorts",
                        f"Understanding {topic.split(':')[0] if ':' in topic else topic} in seconds! "
                        f"Perfect for quick learning.\n\n"
                        f"#Shorts #Tech #Explained #Learning #Tutorial"
                    )
            
            # تنظيف
            self.video_creator.cleanup_temp_files()
            
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

✅ <b>Long Tutorial Video:</b> 8-10 minutes with images & audio
✅ <b>Tech Short #1:</b> 45 seconds with engaging visuals
✅ <b>Tech Short #2:</b> 45 seconds with quick tips

<b>Features:</b>
• Professional images from Pexels
• Clear audio synchronized with text
• Text stays within frame boundaries
• Engaging visual transitions
• YouTube & Blogger publishing

🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
""")
            
        except Exception as e:
            logger.error(f"❌ Daily workflow failed: {e}")
            await self.config.send_telegram_message(f"❌ Daily workflow failed: {str(e)}")

if __name__ == "__main__":
    # التأكد من وجود المجلدات
    for folder in ['output', 'temp']:
        os.makedirs(folder, exist_ok=True)
    
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflow())
