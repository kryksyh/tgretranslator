from telethon import TelegramClient, events
#from telethon import sync
from telethon.tl.functions.channels import CreateChannelRequest, CheckUsernameRequest, UpdateUsernameRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from config import API_HASH, API_ID
from easysettings import EasySettings
import logging


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.WARNING)
settings = EasySettings("configuration.conf")
config_channel = None
source_channel = None
recepients = settings.get("recepients")
wait_for_source_forward = False


if not recepients:
    recepients = []

async def init_config_channel():
    try:
        invite = settings.get("config_channel")
        config_channel = await client.get_entity(invite)
        if config_channel:
            return config_channel
    except:
        pass

    print("Config channel not found creating new one")
    channel = await client(CreateChannelRequest("config_channel", "Message retranslation control room", megagroup=False))
    invite = await client(ExportChatInviteRequest(channel.updates[1].channel_id))
    config_channel = await client.get_entity(invite.link)
    settings.set("config_channel", invite.link)
    settings.save()
    print("Config channel invite link: ", invite.link)
    return config_channel


async def init_source_channel():
    global source_channel
    try:
        link = settings.get("source_channel")
        source_channel = await client.get_entity(link)
    except:
        await client.send_message(config_channel, "Source channel not found or blocked")
    return source_channel

with TelegramClient('anon', API_ID, API_HASH) as client:
    print("Check for config channel")
    config_channel = client.loop.run_until_complete(init_config_channel())
    source_channel = client.loop.run_until_complete(init_source_channel())
    client.loop.run_until_complete(client.send_message(config_channel, "Bot started"))
    


async def update_config_channel(invite_link):
    global config_channel
    try:
        channel = await client.get_entity(invite_link)
        if channel:
            print(channel)
            settings.set("config_channel", invite_link)
            settings.save()
            config_channel = channel
            await client.send_message(config_channel, "New configuration channel active")
        else:
            raise Exception('Channel not found')
    except:
        await client.send_message(config_channel, "Failed to change config channel to: " + invite_link)


async def unknown_command_response():
    await client.send_message(config_channel, "Unknown command")


async def get_id_by_dialog_title(title):
    try:
        dialogs = await client.get_dialogs()
        dialog = [dialog for dialog in dialogs if title in dialog.title]
        if len(dialog) > 1:
            raise Exception("More than one dialog with that name")
        if led(dialog) == 0:
            raise Exception("No such dialogs found")
        return dialog.id
    except:
        await client.send_message(config_channel, "Failed to find dialog with name: " + title)

async def update_source_channel(link):
    global source_channel
    try:
        channel = await client.get_entity(link)
        if channel:
            print(channel)
            settings.set("source_channel", link)
            settings.save()
            source_channel = channel
            await client.send_message(config_channel, "Source channel accepted")
        else:
            raise Exception("Channel not found")
    except:
        await client.send_message(config_channel, "Failed to set source channel to: " + link)


async def add_recepient(recepient):
    global recepients
    try:
        r = await client.get_entity(recepient)
        if r:
            recepients.append(recepient)
            settings.set("recepients", recepients)
            settings.save()
            await client.send_message(config_channel, "Recepient added")
        else:
            raise Exception("Recepient not found")
    except:
        await client.send_message(config_channel, "Failed to add recepient: " + recepient)
        

async def remove_recepient(recepient):
    global recepients
    try:
        recepients.remove(recepient)
        settings.set("recepients", recepients)
        settings.save()
        await client.send_message(config_channel, "Recepient removed")
    except:
        await client.send_message(config_channel, "Failed to remove: " + recepient)
        

async def list_recepients():
    text = "\n".join(recepients)
    if text:
        await client.send_message(config_channel, text)
    else:
        await client.send_message(config_channel, "No recepients added")

@client.on(events.NewMessage)
async def my_event_handler(event):
    global wait_for_source_forward
    chat = await event.get_chat()
    sender = await event.get_sender()
        
    if type(chat).__name__ == "Channel" and chat.title == config_channel.title:
        print(event)
        print(dir(event))
        fwd_from = event.original_update.message.fwd_from
        if fwd_from and wait_for_source_forward and fwd_from.channel_id:
            await update_source_channel(fwd_from.channel_id)
            wait_for_source_forward = False
            return
    
        print("Command received")
        command, *args = event.raw_text.split(':')
        command = command.strip()
        args = "".join(args).strip()
        if command == "set source by url":
            print("Updating source dialog to: ", args)
            await update_source_channel(args)
        elif command == "set source by name":
            print("Updating source dialog to: ", args)
            await update_source_channel(get_id_by_dialog_title(args))
        elif command == "set source by message":
            await client.send_message(message="Please forward message from another channel to set it as source...", entity=config_channel)
            wait_for_source_forward = True
        elif command == "set config channel":
            print("Updating control channel to: ", args)
            await update_config_channel(args)
        elif command == "add recepient":
            print("Adding new recepient: ", args)
            await add_recepient(args)
        elif command == "remove recepient":
            print("Removing recepient: ", args)
            await remove_recepient(args)
        elif command == "list recepients":
            print("Printing recepients list")
            await list_recepients()
        elif command == "help":
            await client.send_message(message="""
set source by url: USERNAME or INVITE_LINK
set source by name: DIALOG NAME
set source by message
set config channel: INVITE_LINK
add recepient: USERNAME or INVITE_LINK
remove recepient: USERNAME or INVITE_LINK
list recepients
""", entity=config_channel)
        else:
            print("Unknown command")
            await unknown_command_response()
    
    # await client.send_message(message=event.raw_text, entity=config_channel)
    if chat ==  source_channel:
        print(event)
        print("got it")
        for rec in recepients:
            entity = await client.get_entity(rec)
            await client.send_message(message=event.message, entity=entity)
    else:
        print(chat.username)
    

client.start()
client.run_until_disconnected()
