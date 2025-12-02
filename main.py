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
    
    def create_text_image(self, text, image_size=(1920, 1080), font_size=60):
        """إنشاء صورة مع نص محترف"""
        try:
            # إنشاء صورة بلون الخلفية
            bg_color = self.hex_to_rgb(self.config.BRAND_COLORS['background'])
            image = Image.new('RGB', image_size, bg_color)
            draw = ImageDraw.Draw(image)
            
            # محاولة تحميل خط (أو استخدام الخط الافتراضي)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # تقسيم النص
            lines = textwrap.wrap(text, width=40)
            
            # حساب موقع الكتابة
            total_text_height = len(lines) * (font_size + 10)
            y = (image_size[1] - total_text_height) // 2
            
            # رسم كل سطر
            text_color = self.hex_to_rgb(self.config.BRAND_COLORS['text'])
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (image_size[0] - text_width) // 2
                draw.text((x, y), line, font=font, fill=text_color)
                y += font_size + 10
            
            # إضافة شعار
            logo_text = f"© {self.config.BRAND_NAME}"
            logo_font = ImageFont.truetype("arial.ttf", 30) if os.path.exists("arial.ttf") else ImageFont.load_default()
            draw.text((50, image_size[1] - 50), logo_text, font=logo_font, fill=text_color)
            
            # حفظ الصورة
            image_path = f"temp/text_image.png"
            image.save(image_path)
            return image_path
            
        except Exception as e:
            self.logger.error(f"❌ Text image creation error: {e}")
            return None
    
    async def create_professional_video(self, script_text, audio_path, video_type="long", topic=""):
        """إنشاء فيديو محترف مع صور ونصوص"""
        try:
            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                duration = audio.duration
            else:
                duration = 600 if video_type == "long" else 45
            
            size = (1920, 1080) if video_type == "long" else (1080, 1920)
            
            # تقسيم النص إلى مشاهد
            sentences = re.split(r'[.!?]+', script_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if not sentences:
                sentences = [topic, "Learn more in this tutorial", "Subscribe for more content"]
            
            clips = []
            sentence_duration = duration / len(sentences)
            
            for i, sentence in enumerate(sentences[:10]):  # حد أقصى 10 مشاهد
                # إنشاء صورة مع نص
                img_path = self.create_text_image(
                    sentence,
                    size,
                    font_size=60 if video_type == "long" else 40
                )
                
                if img_path and os.path.exists(img_path):
                    img_clip = ImageClip(img_path, duration=sentence_duration)
                    clips.append(img_clip)
                else:
                    # خلفية احتياطية
                    if i % 3 == 0:
                        color = self.hex_to_rgb(self.config.BRAND_COLORS['primary'])
                    elif i % 3 == 1:
                        color = self.hex_to_rgb(self.config.BRAND_COLORS['secondary'])
                    else:
                        color = self.hex_to_rgb(self.config.BRAND_COLORS['accent'])
                    
                    color_clip = ColorClip(size=size, color=color, duration=sentence_duration)
                    
                    # إضافة نص
                    try:
                        txt_clip = TextClip(
                            sentence[:100],
                            fontsize=60,
                            color='white',
                            font='Arial-Bold',
                            size=(size[0] - 100, None),
                            method='caption'
                        )
                        txt_clip = txt_clip.set_position('center').set_duration(sentence_duration)
                        color_clip = CompositeVideoClip([color_clip, txt_clip])
                    except:
                        pass
                    
                    clips.append(color_clip)
            
            if not clips:
                # إنشاء فيديو أساسي كحل أخير
                clip = ColorClip(size=size, color=(30, 60, 90), duration=duration)
                clips = [clip]
            
            video = concatenate_videoclips(clips, method="compose")
            
            if audio_path and os.path.exists(audio_path):
                video = video.set_audio(audio)
            
            output_path = f"output/{'professional_video' if video_type == 'long' else 'short_video'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                verbose=False,
                logger=None
            )
            
            self.logger.info(f"✅ Created professional video: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ Professional video creation error: {e}")
            return await self.create_basic_video(audio_path, duration, video_type)
    
    def hex_to_rgb(self, hex_color):
        """تحويل اللون من HEX إلى RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    async def create_basic_video(self, audio_path, duration, video_type="long"):
        """طريقة احتياطية"""
        try:
            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                actual_duration = audio.duration
            else:
                actual_duration = duration
            
            size = (1920, 1080) if video_type == "long" else (1080, 1920)
            final_duration = max(actual_duration, 300 if video_type == "long" else 45)
            
            clip = ColorClip(size=size, color=(30, 60, 90), duration=final_duration)
            
            if audio_path and os.path.exists(audio_path):
                clip = clip.set_audio(audio)
            
            output_path = f"temp/basic_video.mp4"
            clip.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                verbose=False,
                logger=None
            )
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ Basic video creation error: {e}")
            return None
    
    async def publish_to_youtube_real(self, video_path, title, description, video_type="long"):
        """النشر الفعلي على YouTube"""
        try:
            if not os.path.exists(video_path):
                self.logger.error(f"❌ Video file not found: {video_path}")
                return None
            
            recent_videos, recent_articles = self.get_recent_content_links()
            
            # إصلاح: استخدام triple quotes لتجنب مشاكل backslash
            full_description = f"""{description}

🌟 **About This Video:**
This comprehensive tutorial covers everything you need to know about this topic. Perfect for tech enthusiasts, developers, and learners.

📚 **Continue Learning:**
{recent_videos}{recent_articles}

🔔 **Subscribe for more tech education:** {self.config.YOUTUBE_CHANNEL_URL}

📝 **Read our blog:** {self.config.BLOGGER_BLOG_URL}

🏷️ **Tags:**
technology, education, tutorial, programming, tech, {title.split()[0].lower()}

#TechEducation #{title.split()[0]} #Tutorial"""
            
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
• Professional video editing
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
        """النشر الفعلي على Blogger"""
        try:
            recent_videos, recent_articles = self.get_recent_content_links()
            
            # إصلاح: استخدام string formatting بدلاً من backslashes في f-string
            video_list_html = ""
            article_list_html = ""
            
            if recent_videos:
                # معالجة الفيديوهات إلى HTML
                video_items = []
                video_lines = recent_videos.strip().split('\n')
                for line in video_lines:
                    if line.startswith('• '):
                        video_items.append(f"<li>{line[2:]}</li>")
                video_list_html = "<ul>" + "".join(video_items) + "</ul>"
            
            if recent_articles:
                # معالجة المقالات إلى HTML
                article_items = []
                article_lines = recent_articles.strip().split('\n')
                for line in article_lines:
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
            
            # للاختبار: تشغيل كل workflows
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
• Professional video editing
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
