import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import AudioParameters, HighQualityAudio
from pytgcalls.types.input_stream import AudioStream, AudioPiped
import youtube_dl
from config import *

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
}

app = Client(SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
call = PyTgCalls(app)

current_stream = None
is_playing = False
queue = []

@app.on_message(filters.command("play") & filters.user(ADMIN_ID))
async def play_music(client: Client, message: Message):
    global current_stream, is_playing, queue
    
    if len(message.command) < 2:
        await message.reply("Напиши: play название трека или ссылка")
        return
    
    query = " ".join(message.command[1:])
    status_msg = await message.reply(f"Ищу: {query}...")
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info['webpage_url']
            title = info['title']
            
            if is_playing:
                queue.append({'url': url, 'title': title})
                await status_msg.edit(f"Добавлено в очередь: {title}")
                return
            
            current_stream = AudioPiped(
                url,
                audio_parameters=AudioParameters.from_quality(HighQualityAudio())
            )
            
            try:
                await call.join_group_call(CHAT_ID, current_stream, stream_type=StreamType().local_stream)
                is_playing = True
                await status_msg.edit(f"Сейчас играет: {title}")
            except Exception as e:
                await status_msg.edit(f"Ошибка: {str(e)}")
                
    except Exception as e:
        await status_msg.edit(f"Не удалось найти трек. Ошибка: {str(e)[:100]}")

@app.on_message(filters.command("pause") & filters.user(ADMIN_ID))
async def pause_music(client: Client, message: Message):
    global is_playing
    try:
        await call.pause_stream(CHAT_ID)
        is_playing = False
        await message.reply("Пауза")
    except:
        await message.reply("Ничего не играет")

@app.on_message(filters.command("resume") & filters.user(ADMIN_ID))
async def resume_music(client: Client, message: Message):
    global is_playing
    try:
        await call.resume_stream(CHAT_ID)
        is_playing = True
        await message.reply("Продолжаю")
    except:
        await message.reply("Не могу продолжить")

@app.on_message(filters.command("skip") & filters.user(ADMIN_ID))
async def skip_music(client: Client, message: Message):
    global current_stream, is_playing, queue
    
    if not is_playing:
        await message.reply("Ничего не играет")
        return
    
    try:
        await call.leave_group_call(CHAT_ID)
        is_playing = False
        
        if queue:
            next_track = queue.pop(0)
            current_stream = AudioPiped(
                next_track['url'],
                audio_parameters=AudioParameters.from_quality(HighQualityAudio())
            )
            await call.join_group_call(CHAT_ID, current_stream, stream_type=StreamType().local_stream)
            is_playing = True
            await message.reply(f"Следующий трек: {next_track['title']}")
        else:
            await message.reply("Трек пропущен. Очередь пуста")
            current_stream = None
            
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

@app.on_message(filters.command("volume") & filters.user(ADMIN_ID))
async def set_volume(client: Client, message: Message):
    if len(message.command) == 2:
        try:
            vol = int(message.command[1])
            if 1 <= vol <= 200:
                await message.reply(f"Громкость {vol} процентов")
            else:
                await message.reply("Громкость от 1 до 200")
        except:
            await message.reply("Напиши volume 50")
    else:
        await message.reply("Использование: volume число")

@app.on_message(filters.command("queue") & filters.user(ADMIN_ID))
async def show_queue(client: Client, message: Message):
    global queue
    
    if not queue:
        await message.reply("Очередь пуста")
        return
    
    queue_list = "Очередь треков:\n"
    for i, track in enumerate(queue[:10], 1):
        queue_list += f"{i}. {track['title']}\n"
    
    await message.reply(queue_list)

@app.on_message(filters.command("clear") & filters.user(ADMIN_ID))
async def clear_queue(client: Client, message: Message):
    global queue
    queue = []
    await message.reply("Очередь очищена")

@app.on_message(filters.command("leave") & filters.user(ADMIN_ID))
async def leave_vc(client: Client, message: Message):
    global is_playing, current_stream, queue
    
    try:
        await call.leave_group_call(CHAT_ID)
        is_playing = False
        current_stream = None
        queue = []
        await message.reply("Вышел из голосового чата")
    except:
        await message.reply("Уже вышел")

@app.on_message(filters.command("radio") & filters.user(ADMIN_ID))
async def start_radio(client: Client, message: Message):
    global current_stream, is_playing
    
    if len(message.command) < 2:
        await message.reply("Напиши: radio ссылка на радиостанцию")
        return
    
    radio_url = message.command[1]
    status_msg = await message.reply(f"Включаю радио: {radio_url}...")
    
    try:
        current_stream = AudioPiped(
            radio_url,
            audio_parameters=AudioParameters.from_quality(HighQualityAudio())
        )
        
        await call.join_group_call(CHAT_ID, current_stream, stream_type=StreamType().local_stream)
        is_playing = True
        await status_msg.edit(f"Радио включено")
        
    except Exception as e:
        await status_msg.edit(f"Ошибка: {str(e)}")

@app.on_message(filters.command("help") & filters.user(ADMIN_ID))
async def show_help(client: Client, message: Message):
    help_text = """
Доступные команды:

play название - поиск и воспроизведение музыки
pause - пауза
resume - продолжить
skip - следующий трек
queue - показать очередь
clear - очистить очередь
volume 1-200 - изменить громкость
radio ссылка - включить интернет радио
leave - выйти из голосового чата
help - показать это сообщение
"""
    await message.reply(help_text)

async def main():
    await call.start()
    await app.start()
    print("Бот успешно запущен")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
