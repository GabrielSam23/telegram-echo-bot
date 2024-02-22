import os
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_components import create_select, create_select_option, wait_for_component
from keep_alive import keep_alive

keep_alive()

# Configurações
# Substitua 'seu_token_aqui' pelo token do seu bot
TOKEN = os.environ.get('TOKEN')
PREFIX = '!'  # Prefixo de comando do bot
# ID do canal onde as respostas do formulário serão enviadas
FORM_CHANNEL_ID = 1208921193294332034
CANAL_ADMITIDOS_ID = 1208917475211612170  # ID do canal para admissões aceitas
CANAL_NEGADOS_ID = 1208917509307244554  # ID do canal para admissões negadas

FORM_FIELDS = [
    "Nome",
    "Idade",
    "E-mail",
    "Telefone"
]

# Variáveis globais para armazenar o estado do envio da mensagem de orientação
orientacao_enviada = False

# Variável global para armazenar o ID da mensagem original do formulário de admissão
form_message_ids = {}

# Inicialização do bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
slash = SlashCommand(bot, sync_commands=True)


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    print('Pronto para receber formulários de admissão.')
    global orientacao_enviada
    if not orientacao_enviada:
        await enviar_orientacao()
        orientacao_enviada = True


async def enviar_orientacao():
    canal_orientacao_id = 1208915700178100274  # ID do canal de orientação
    canal_orientacao = bot.get_channel(canal_orientacao_id)
    if canal_orientacao:
        embed_orientacao = discord.Embed(
            title="Bem-vindo ao servidor!",
            description="Aqui você encontrará todas as informações necessárias para se juntar à nossa comunidade.",
            color=discord.Color.green()
        )
        embed_orientacao.set_thumbnail(
            url="https://example.com/seu_logo.png")
        embed_orientacao.add_field(
            name="Como se candidatar?", value="Para se candidatar, utilize o comando `!enviarformulario` e preencha o formulário que será enviado em seguida.")
        embed_orientacao.add_field(
            name="Dúvidas?", value="Se tiver alguma dúvida, não hesite em entrar em contato com a equipe de moderação.")
        embed_orientacao.set_footer(
            text="Obrigado por escolher nosso servidor!")
        try:
            await canal_orientacao.send(embed=embed_orientacao)
        except Exception as e:
            print(f"Erro ao enviar a mensagem de orientação: {e}")
    else:
        print("Canal de orientação não encontrado.")


@bot.command()
async def enviarformulario(ctx):
    # Envia as instruções
    embed = discord.Embed(title="Formulário de Admissão",
                          description="Por favor, preencha o formulário abaixo com as informações solicitadas:",
                          color=discord.Color.blue())
    # Adiciona campos vazios ao embed para cada campo do formulário
    for field in FORM_FIELDS:
        embed.add_field(
            name=field, value="Digite sua resposta aqui", inline=False)

    # Adicionando campo de disponibilidade com menu suspenso
    select = create_select(
        options=[
            create_select_option("Manhã", "manha"),
            create_select_option("Tarde", "tarde"),
            create_select_option("Noite", "noite"),
            create_select_option("Todas as opções", "todas")
        ],
        placeholder="Selecione sua disponibilidade",
        custom_id="disponibilidade"
    )

    message = await ctx.send(embed=embed, components=[select])

    # Inicializa as respostas
    respostas = {}

    # Aguarda a seleção da disponibilidade
    interaction = await wait_for_component(bot, components=select)
    disponibilidade = interaction.selected_options[0]
    respostas["Disponibilidade"] = disponibilidade

    # Atualiza o embed com a resposta de disponibilidade
    embed.set_field_at(0, name="Disponibilidade", value=disponibilidade, inline=False)
    await message.edit(embed=embed)

    # Atualiza o embed com as respostas fornecidas
    for field in FORM_FIELDS:
        await ctx.send(f"Por favor, digite sua resposta para {field}:")
        response = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        respostas[field] = response.content
        # Atualiza o embed com a resposta fornecida
        embed.set_field_at(FORM_FIELDS.index(
            field), name=field, value=response.content)

        await message.edit(embed=embed)

    # Constrói uma mensagem com as respostas
    # Menciona o autor do formulário
    response_message = f"Respostas do formulário de {ctx.author.mention}:\n"
    for field, answer in respostas.items():
        response_message += f"{field}: {answer}\n"

    # Envia as respostas do formulário para o canal específico
    channel = bot.get_channel(FORM_CHANNEL_ID)
    if channel:
        form_message = await channel.send(response_message)
        # Armazena o ID da mensagem original do formulário de admissão
        form_message_ids[form_message.id] = ctx.author.id
        # Adiciona reações à mensagem do formulário
        await form_message.add_reaction('✅')  # Reação de confirmação
        await form_message.add_reaction('❌')  # Reação de negação
        await ctx.send("Seu formulário foi enviado com sucesso. Aguarde uma resposta.")
    else:
        await ctx.send(f'Não foi possível enviar o formulário no momento. Por favor, tente novamente mais tarde.')


@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    if reaction.message.channel.id == FORM_CHANNEL_ID:
        # Verifica se a mensagem original do formulário de admissão está registrada
        if reaction.message.id in form_message_ids:
            author_id = form_message_ids[reaction.message.id]
            author = await bot.fetch_user(author_id)
            if str(reaction.emoji) == '✅':
                await aceitar_admissao(reaction, author)
            elif str(reaction.emoji) == '❌':
                await recusar_admissao(reaction, author)


async def aceitar_admissao(reaction, author):
    canal_admitidos = bot.get_channel(CANAL_ADMITIDOS_ID)
    if canal_admitidos:
        try:
            await reaction.message.delete()
            mensagem_admitido = f"Parabéns! A admissão de {author.mention} foi aceita. Bem-vindo à nossa comunidade!"
            await canal_admitidos.send(mensagem_admitido)
            await author.send("Parabéns! Sua admissão foi aceita. Bem-vindo à nossa comunidade!")
        except Exception as e:
            print(f"Erro ao aceitar admissão: {e}")
    else:
        print("Canal de admissões aceitas não encontrado.")


async def recusar_admissao(reaction, author):
    canal_negados = bot.get_channel(CANAL_NEGADOS_ID)
    if canal_negados:
        try:
            await reaction.message.delete()
            mensagem_negado = f"A admissão de {author.mention} foi recusada. Entre em contato conosco para mais informações."
            await canal_negados.send(mensagem_negado)
            await author.send("Sua admissão foi recusada. Entre em contato conosco para mais informações.")
        except Exception as e:
            print(f"Erro ao recusar admissão: {e}")
    else:
        print("Canal de admissões negadas não encontrado.")


bot.run(TOKEN)
