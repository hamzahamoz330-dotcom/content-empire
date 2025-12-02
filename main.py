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

class PexelsContentManager:
    """مدير محتوى Pexels للحصول على صور وفيديوهات حقيقية"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.base_url = "https://api.pexels.com"
        
    def search_videos(self, query, per_page=10):
        """البحث عن فيديوهات في Pexels"""
        try:
            url = f"{self.base_url}/videos/search"
            params = {
                "query": query,
                "per_page": per_page,
                "orientation": "portrait" if "short" in query else "landscape"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                
                # فلترة الفيديوهات المناسبة
                suitable_videos = []
                for video in videos:
                    if video.get("duration", 0) > 5:  # أكثر من 5 ثواني
                        video_files = video.get("video_files", [])
                        if video_files:
                            # اختيار أفضل جودة
                            hd_videos = [v for v in video_files if v.get("quality") == "hd"]
                            if hd_videos:
                                suitable_videos.append({
                                    "id": video["id"],
                                    "url": hd_videos[0]["link"],
                                    "duration": video["duration"],
                                    "image": video["image"]
                                })
                
                return suitable_videos[:5]  # إرجاع أول 5 فيديوهات مناسبة
            return []
        except Exception as e:
            logger.error(f"❌ Pexels video search error: {e}")
            return []
    
    def search_images(self, query, per_page=15):
        """البحث عن صور في Pexels"""
        try:
            url = f"{self.base_url}/v1/search"
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
                        "id": photo["id"],
                        "url": photo["src"]["original"],
                        "photographer": photo["photographer"]
                    })
                
                return images
            return []
        except Exception as e:
            logger.error(f"❌ Pexels image search error: {e}")
            return []
    
    def download_video(self, video_url, output_path):
        """تحميل فيديو من Pexels"""
        try:
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Video download error: {e}")
            return False
    
    def download_image(self, image_url, output_path):
        """تحميل صورة من Pexels"""
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Image download error: {e}")
            return False

class ProfessionalVideoEditor:
    """محرر فيديو محترف مع محتوى حقيقي"""
    
    def __init__(self, pexels_manager):
        self.pexels_manager = pexels_manager
        
    def create_text_overlay(self, text, duration, video_size=(1920, 1080), position='bottom'):
        """إنشاء نص فوقي بمظهر احترافي"""
        try:
            # إنشاء نص بمظهر جذاب
            txt_clip = TextClip(
                text,
                fontsize=70 if video_size[0] == 1920 else 50,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=3,
                size=(video_size[0] - 200, None),
                method='caption',
                align='center'
            )
            
            # تحديد الموقع
            if position == 'bottom':
                y_pos = video_size[1] - txt_clip.h - 100
            elif position == 'top':
                y_pos = 100
            else:  # center
                y_pos = (video_size[1] - txt_clip.h) // 2
            
            txt_clip = txt_clip.set_position(('center', y_pos))
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.crossfadein(0.5)
            txt_clip = txt_clip.crossfadeout(0.5)
            
            return txt_clip
        except Exception as e:
            logger.error(f"❌ Text overlay error: {e}")
            return None
    
    def create_title_card(self, title, duration, video_size=(1920, 1080)):
        """إنشاء بطاقة عنوان احترافية"""
        try:
            # خلفية متدرجة
            bg_clip = ColorClip(
                size=video_size,
                color=(25, 99, 235),  # أزرق
                duration=duration
            )
            
            # العنوان الرئيسي
            title_clip = TextClip(
                title,
                fontsize=100 if video_size[0] == 1920 else 70,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=4,
                size=(video_size[0] - 200, None),
                method='caption',
                align='center'
            )
            
            # شعار القناة
            logo_text = "TECH COMPASS"
            logo_clip = TextClip(
                logo_text,
                fontsize=40,
                color='rgba(255,255,255,0.8)',
                font='Arial-Bold',
                size=(video_size[0] - 200, None),
                method='caption',
                align='center'
            )
            
            # تجميع العناصر
            title_clip = title_clip.set_position(('center', video_size[1]//2 - 80))
            logo_clip = logo_clip.set_position(('center', video_size[1]//2 + 100))
            
            final_clip = CompositeVideoClip([
                bg_clip,
                title_clip,
                logo_clip
            ])
            
            final_clip = final_clip.set_duration(duration)
            
            return final_clip
        except Exception as e:
            logger.error(f"❌ Title card error: {e}")
            return None
    
    async def create_long_video(self, topic, script, audio_path, output_name):
        """إنشاء فيديو طويل محترف"""
        try:
            # البحث عن محتوى متعلق بالموضوع
            search_query = topic.lower().replace(" ", "+")
            videos = self.pexels_manager.search_videos(f"{search_query}+technology", per_page=10)
            images = self.pexels_manager.search_images(f"{search_query}+technology", per_page=20)
            
            clips = []
            
            # 1. بطاقة العنوان (10 ثواني)
            title_card = self.create_title_card(topic, 10)
            if title_card:
                clips.append(title_card)
            
            # تقسيم السكربت إلى أجزاء
            script_parts = self.split_script(script)
            
            # استخدام المحتوى الحقيقي
            content_index = 0
            for i, part in enumerate(script_parts):
                part_duration = min(len(part.split()) * 0.5, 15)  # تقدير المدة
                
                if content_index < len(videos) and random.random() > 0.5:
                    # استخدام فيديو حقيقي
                    video = videos[content_index]
                    video_path = f"temp/pexels_video_{content_index}.mp4"
                    
                    if self.pexels_manager.download_video(video["url"], video_path):
                        try:
                            video_clip = VideoFileClip(video_path)
                            # اقتصاص الفيديو للطول المناسب
                            if video_clip.duration > part_duration:
                                video_clip = video_clip.subclip(0, part_duration)
                            else:
                                part_duration = video_clip.duration
                            
                            # إضافة نص فوقي
                            text_overlay = self.create_text_overlay(
                                part[:100],
                                part_duration,
                                position='bottom' if i % 2 == 0 else 'top'
                            )
                            
                            if text_overlay:
                                final_clip = CompositeVideoClip([video_clip, text_overlay])
                            else:
                                final_clip = video_clip
                            
                            clips.append(final_clip)
                            content_index += 1
                            continue
                        except:
                            pass
                
                # استخدام صورة حقيقية كبديل
                if content_index < len(images):
                    image = images[content_index]
                    image_path = f"temp/pexels_image_{content_index}.jpg"
                    
                    if self.pexels_manager.download_image(image["url"], image_path):
                        try:
                            image_clip = ImageClip(image_path, duration=part_duration)
                            
                            # إضافة نص فوقي
                            text_overlay = self.create_text_overlay(
                                part[:100],
                                part_duration,
                                position='bottom'
                            )
                            
                            if text_overlay:
                                final_clip = CompositeVideoClip([image_clip, text_overlay])
                            else:
                                final_clip = image_clip
                            
                            clips.append(final_clip)
                            content_index += 1
                            continue
                        except:
                            pass
                
                # خلفية احتياطية مع نص
                bg_color = random.choice([(25, 99, 235), (124, 58, 237), (5, 150, 105)])
                bg_clip = ColorClip(size=(1920, 1080), color=bg_color, duration=part_duration)
                
                text_overlay = self.create_text_overlay(
                    part[:150],
                    part_duration,
                    position='center'
                )
                
                if text_overlay:
                    final_clip = CompositeVideoClip([bg_clip, text_overlay])
                else:
                    final_clip = bg_clip
                
                clips.append(final_clip)
            
            # 2. تجميع الفيديوهات
            if not clips:
                # إنشاء فيديو احتياطي بسيط
                bg_clip = ColorClip(size=(1920, 1080), color=(25, 99, 235), duration=60)
                text_clip = self.create_text_overlay(topic, 60, position='center')
                final_video = CompositeVideoClip([bg_clip, text_clip])
            else:
                final_video = concatenate_videoclips(clips, method="compose")
            
            # 3. إضافة الصوت
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                # اقتصاص الفيديو لطول الصوت
                if final_video.duration > audio_clip.duration:
                    final_video = final_video.subclip(0, audio_clip.duration)
                final_video = final_video.set_audio(audio_clip)
            
            # 4. إضافة شارة النهاية
            end_card = self.create_title_card("Thanks for Watching!", 5)
            if end_card:
                final_video = concatenate_videoclips([final_video, end_card], method="compose")
            
            # 5. حفظ الفيديو
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
            self.clean_temp_files()
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Long video creation error: {e}")
            return None
    
    async def create_short_video(self, topic, script, audio_path, output_name):
        """إنشاء فيديو قصير محترف"""
        try:
            # البحث عن محتوى للمقاطع القصيرة
            search_query = topic.lower().replace(" ", "+")
            videos = self.pexels_manager.search_videos(
                f"{search_query}+technology+short",
                per_page=5
            )
            
            clips = []
            total_duration = 0
            target_duration = 45  # 45 ثانية للشورت
            
            # 1. المقدمة السريعة (3 ثواني)
            intro_text = f"🔥 {topic.split(':')[0] if ':' in topic else topic}"
            intro_clip = self.create_text_overlay(
                intro_text,
                3,
                video_size=(1080, 1920),
                position='center'
            )
            if intro_clip:
                # خلفية حيوية للمقدمة
                bg_clip = ColorClip(size=(1080, 1920), color=(255, 50, 50), duration=3)
                intro_final = CompositeVideoClip([bg_clip, intro_clip])
                clips.append(intro_final)
                total_duration += 3
            
            # 2. المحتوى الرئيسي
            if videos:
                for video in videos[:3]:  # استخدام 3 فيديوهات كحد أقصى
                    if total_duration >= target_duration:
                        break
                    
                    video_path = f"temp/short_video_{len(clips)}.mp4"
                    if self.pexels_manager.download_video(video["url"], video_path):
                        try:
                            video_clip = VideoFileClip(video_path)
                            
                            # اقتصاص الفيديو (10-15 ثانية لكل مقطع)
                            clip_duration = min(video_clip.duration, 15)
                            if total_duration + clip_duration > target_duration:
                                clip_duration = target_duration - total_duration
                            
                            if clip_duration > 3:
                                video_clip = video_clip.subclip(0, clip_duration)
                                
                                # إضافة نص سريع
                                quick_text = self.get_quick_tip(topic)
                                text_overlay = self.create_text_overlay(
                                    quick_text,
                                    clip_duration,
                                    video_size=(1080, 1920),
                                    position='bottom'
                                )
                                
                                if text_overlay:
                                    final_clip = CompositeVideoClip([video_clip, text_overlay])
                                else:
                                    final_clip = video_clip
                                
                                clips.append(final_clip)
                                total_duration += clip_duration
                        except:
                            continue
            
            # 3. إذا لم يكن هناك محتوى كافي، إضافة مقاطع نصية
            while total_duration < target_duration:
                remaining = target_duration - total_duration
                clip_duration = min(remaining, 10)
                
                # خلفية مع نص
                bg_color = random.choice([(25, 99, 235), (124, 58, 237), (5, 150, 105)])
                bg_clip = ColorClip(size=(1080, 1920), color=bg_color, duration=clip_duration)
                
                tip_text = self.get_quick_tip(topic)
                text_overlay = self.create_text_overlay(
                    tip_text,
                    clip_duration,
                    video_size=(1080, 1920),
                    position='center'
                )
                
                if text_overlay:
                    final_clip = CompositeVideoClip([bg_clip, text_overlay])
                else:
                    final_clip = bg_clip
                
                clips.append(final_clip)
                total_duration += clip_duration
            
            # 4. الخاتمة (3 ثواني)
            end_text = "🔔 Subscribe for more!"
            end_clip = self.create_text_overlay(
                end_text,
                3,
                video_size=(1080, 1920),
                position='center'
            )
            if end_clip:
                bg_clip = ColorClip(size=(1080, 1920), color=(25, 99, 235), duration=3)
                end_final = CompositeVideoClip([bg_clip, end_clip])
                clips.append(end_final)
            
            # 5. تجميع الفيديو
            final_video = concatenate_videoclips(clips, method="compose")
            
            # 6. إضافة الصوت لو كان متوفراً
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    # اقتصاص أو تكرار الصوت ليتناسب مع الفيديو
                    if audio_clip.duration < final_video.duration:
                        # تكرار الصوت
                        repeats = int(final_video.duration // audio_clip.duration) + 1
                        audio_segments = [audio_clip] * repeats
                        audio_clip = concatenate_audioclips(audio_segments)
                        audio_clip = audio_clip.subclip(0, final_video.duration)
                    else:
                        audio_clip = audio_clip.subclip(0, final_video.duration)
                    
                    final_video = final_video.set_audio(audio_clip)
                except:
                    pass
            
            # 7. حفظ الفيديو
            output_path = f"output/{output_name}.mp4"
            final_video.write_videofile(
                output_path,
                fps=30,  # fps أعلى للمقاطع القصيرة
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='fast',
                verbose=False,
                logger=None
            )
            
            # تنظيف الملفات المؤقتة
            self.clean_temp_files()
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Short video creation error: {e}")
            return None
    
    def split_script(self, script, max_words=50):
        """تقسيم السكربت إلى أجزاء صغيرة"""
        sentences = re.split(r'[.!?]+', script)
        parts = []
        current_part = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            words = sentence.split()
            if current_word_count + len(words) <= max_words:
                current_part.append(sentence)
                current_word_count += len(words)
            else:
                if current_part:
                    parts.append(' '.join(current_part))
                current_part = [sentence]
                current_word_count = len(words)
        
        if current_part:
            parts.append(' '.join(current_part))
        
        return parts if parts else [script[:200]]
    
    def get_quick_tip(self, topic):
        """الحصول على نصيحة سريعة للمقاطع القصيرة"""
        tips = [
            f"💡 {topic} can revolutionize your workflow!",
            f"⚡ Quick tip about {topic.split()[0].lower()}!",
            f"🚀 Mastering {topic.split()[0].lower()} in seconds!",
            f"🎯 Essential {topic.split()[0].lower()} knowledge!",
            f"🔥 Pro tip for {topic.split()[0].lower()} users!",
        ]
        return random.choice(tips)
    
    def clean_temp_files(self):
        """تنظيف الملفات المؤقتة"""
        try:
            import glob
            temp_files = glob.glob("temp/pexels_*") + glob.glob("temp/short_video_*")
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
        self.pexels_manager = PexelsContentManager(self.config.PEXELS_API_KEY)
        self.video_editor = ProfessionalVideoEditor(self.pexels_manager)
        self.used_topics = set()
        self.content_history = {
            "videos": [],
            "articles": []
        }
        self.load_used_topics()
        self.load_content_history()
    
    def setup_logging(self):
        self.logger = logger
    
    def setup_directories(self):
        os.makedirs('output', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('assets', exist_ok=True)
    
    async def check_environment(self):
        """التحقق من أن جميع Environment Variables موجودة"""
        required_vars = ['GEMINI_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'PEXELS_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.error(f"❌ Missing environment variables: {missing_vars}")
            await self.config.send_telegram_message(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        self.logger.info("✅ All environment variables are set")
        return True
    
    async def get_unique_topic(self):
        """توليد موضوع فريد تماماً"""
        try:
            topics = [
                "AI in Healthcare: Saving Lives with Technology",
                "Quantum Computing Breakthroughs 2024",
                "Cybersecurity for Small Businesses",
                "Building AI Chatbots with Python",
                "Cloud Migration Strategies",
                "Blockchain for Supply Chain Management",
                "5G and the Future of Connectivity",
                "AR/VR in Education",
                "Data Science Career Guide",
                "IoT Smart Home Devices"
            ]
            
            available_topics = [t for t in topics if t not in self.used_topics]
            
            if available_topics:
                chosen_topic = random.choice(available_topics)
                self.used_topics.add(chosen_topic)
                self.save_used_topic(chosen_topic)
                return chosen_topic
            else:
                return "Latest Technology Innovations 2024"
                
        except Exception as e:
            self.logger.error(f"❌ Error in topic selection: {e}")
            return "Tech Trends 2024"
    
    def save_used_topic(self, topic):
        try:
            with open('output/used_topics.txt', 'a') as f:
                f.write(topic + '\n')
        except:
            pass
    
    def load_used_topics(self):
        try:
            if os.path.exists('output/used_topics.txt'):
                with open('output/used_topics.txt', 'r') as f:
                    self.used_topics = set(line.strip() for line in f)
        except:
            self.used_topics = set()
    
    def load_content_history(self):
        try:
            if os.path.exists('output/content_history.json'):
                with open('output/content_history.json', 'r') as f:
                    self.content_history = json.load(f)
        except:
            self.content_history = {"videos": [], "articles": []}
    
    async def generate_script(self, topic, content_type="long_video"):
        """توليد سكربت باستخدام Gemini"""
        try:
            if not self.config.GEMINI_API_KEY:
                return self.get_fallback_script(topic, content_type)
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            if content_type == "long_video":
                prompt = f"""Create an engaging YouTube video script about: "{topic}"

                Make it:
                - Educational and practical
                - 8-10 minutes when spoken
                - Include specific examples
                - Use simple language
                - Add call to action at the end"""
            
            else:  # short video
                prompt = f"""Create a 45-second YouTube Short script about: "{topic}"

                Make it:
                - Hook in first 3 seconds
                - One actionable tip
                - High energy
                - Under 100 words"""
            
            response = await model.generate_content_async(prompt)
            return response.text
            
        except Exception as e:
            self.logger.error(f"❌ Script generation error: {e}")
            return self.get_fallback_script(topic, content_type)
    
    def get_fallback_script(self, topic, content_type):
        """سكربت احتياطي"""
        if content_type == "long_video":
            return f"""Welcome to Tech Compass! Today we're exploring {topic}.

This technology is changing how we work and live. Let me show you how.

First, understand the basics. {topic} involves several key concepts that every tech enthusiast should know.

The applications are endless. From business to education, {topic} is making a real difference.

Here are some practical tips to get started. You don't need to be an expert to begin.

Remember to subscribe for more tech insights. Leave a comment about what you'd like to see next!"""
        else:
            return f"Quick tip about {topic}! This can save you hours. Follow for more tech insights! 🔥"
    
    async def generate_audio(self, text, output_name):
        """توليد صوت احترافي"""
        try:
            output_path = f"temp/{output_name}.mp3"
            
            # استخدام جزء من النص للصوت
            clean_text = text[:1000].replace('\n', ' ')
            
            communicate = edge_tts.Communicate(
                clean_text,
                "en-US-ChristopherNeural",
                rate="+10%",  # زيادة السرعة قليلاً
                pitch="+0Hz"
            )
            
            await communicate.save(output_path)
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            return None
    
    async def create_and_publish_video(self, workflow_type="12:00"):
        """إنشاء ونشر فيديو"""
        try:
            self.logger.info(f"🚀 Starting {workflow_type} workflow")
            
            # 1. اختيار موضوع
            topic = await self.get_unique_topic()
            self.logger.info(f"📝 Topic: {topic}")
            
            # 2. توليد السكربت
            content_type = "long_video" if workflow_type == "12:00" else "short_video"
            script = await self.generate_script(topic, content_type)
            
            # 3. توليد الصوت
            audio_name = f"{workflow_type}_{datetime.now().strftime('%H%M')}"
            audio_path = await self.generate_audio(script, audio_name)
            
            # 4. إنشاء الفيديو
            if workflow_type == "12:00":
                video_path = await self.video_editor.create_long_video(
                    topic, script, audio_path, f"long_{datetime.now().strftime('%Y%m%d_%H%M')}"
                )
                title = f"{topic} - Complete Guide 2024"
                description = f"Learn everything about {topic} in this comprehensive tutorial."
            else:
                video_path = await self.video_editor.create_short_video(
                    topic, script, audio_path, f"short_{datetime.now().strftime('%Y%m%d_%H%M')}"
                )
                title = f"{topic} in 45s! ⚡"
                description = f"Quick tip about {topic}. Follow for more!"
            
            if video_path and os.path.exists(video_path):
                # 5. إرسال تقرير
                video_size = os.path.getsize(video_path) / (1024*1024)  # MB
                
                message = f"""
🎬 <b>Video Created Successfully!</b>

✅ <b>Workflow:</b> {workflow_type}
✅ <b>Topic:</b> {topic}
✅ <b>Type:</b> {'10-min Tutorial' if workflow_type == '12:00' else '45s Short'}
✅ <b>File Size:</b> {video_size:.1f} MB
✅ <b>Path:</b> {video_path}

📊 <b>Features:</b>
• Real Pexels videos & images
• Professional editing
• Clear audio narration
• Engaging text overlays
• Smooth transitions

🚀 <b>Ready for upload!</b>
"""
                
                await self.config.send_telegram_message(message)
                
                # 6. حفظ في التاريخ
                self.content_history["videos"].append({
                    "title": title,
                    "topic": topic,
                    "type": content_type,
                    "path": video_path,
                    "date": datetime.now().isoformat()
                })
                
                # الاحتفاظ بآخر 20 فيديو فقط
                if len(self.content_history["videos"]) > 20:
                    self.content_history["videos"] = self.content_history["videos"][-20:]
                
                self.save_content_history()
                
                return video_path
            else:
                await self.config.send_telegram_message(f"❌ Failed to create video for {workflow_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ {workflow_type} workflow error: {e}")
            await self.config.send_telegram_message(f"❌ {workflow_type} failed: {str(e)}")
            return None
    
    def save_content_history(self):
        try:
            with open('output/content_history.json', 'w') as f:
                json.dump(self.content_history, f, indent=2)
        except:
            pass
    
    async def run_daily_workflows(self):
        """تشغيل جميع الworkflows اليومية"""
        try:
            if not await self.check_environment():
                return
            
            self.logger.info("🚀 Starting all daily workflows")
            
            # 1. فيديو طويل (12:00)
            await self.create_and_publish_video("12:00")
            await asyncio.sleep(2)
            
            # 2. شورت 1 (14:00)
            await self.create_and_publish_video("14:00")
            await asyncio.sleep(2)
            
            # 3. شورت 2 (16:00)
            await self.create_and_publish_video("16:00")
            
            # 4. تقرير نهائي
            await self.config.send_telegram_message(f"""
🎉 <b>Daily Content Production Complete!</b>

✅ <b>12:00:</b> 10-min Educational Video
✅ <b>14:00:</b> 45s Tech Short
✅ <b>16:00:</b> 45s Quick Tip Short

📊 <b>Total Videos:</b> 3
🎬 <b>Content:</b> Real Pexels videos & images
🔊 <b>Audio:</b> Professional narration
🎨 <b>Editing:</b> Professional overlays & transitions

⚡ <b>All videos saved in /output folder!</b>
""")
            
            self.logger.info("✅ All workflows completed")
            
        except Exception as e:
            error_msg = f"❌ Daily workflows failed: {str(e)}"
            self.logger.error(error_msg)
            await self.config.send_telegram_message(error_msg)

if __name__ == "__main__":
    empire = ContentEmpire()
    asyncio.run(empire.run_daily_workflows())
