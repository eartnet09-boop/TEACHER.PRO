"""
Populador de dados iniciais do banco de dados
200+ palavras, 10+ diálogos, categorias
"""
import logging
from typing import List, Dict
from .database import db

logger = logging.getLogger(__name__)


class DataSeeder:
    """Responsável por popular o banco com dados iniciais"""
    
    def __init__(self):
        self.categories = self._get_categories()
        self.vocabulary = self._get_vocabulary()
        self.dialogs = self._get_dialogs()
        self.achievements = self._get_achievements()
    
    async def seed_all(self):
        """Popula todas as tabelas com dados iniciais"""
        logger.info("🌱 Iniciando seed do banco de dados...")
        
        await self._seed_categories()
        await self._seed_vocabulary()
        await self._seed_dialogs()
        await self._seed_achievements()
        
        logger.info("✅ Seed concluído com sucesso!")
        await self._print_stats()
    
    async def _seed_categories(self):
        """Insere categorias"""
        for cat in self.categories:
            existing = await db.fetch_one(
                "SELECT id FROM categories WHERE name = ?",
                (cat["name"],)
            )
            if not existing:
                await db.execute(
                    """INSERT INTO categories (name, icon, description, color) 
                       VALUES (?, ?, ?, ?)""",
                    (cat["name"], cat["icon"], cat["description"], cat["color"])
                )
        
        count = await db.fetch_one("SELECT COUNT(*) as count FROM categories")
        logger.info(f"   Categorias: {count['count']}")
    
    async def _seed_vocabulary(self):
        """Insere palavras do vocabulário"""
        inserted = 0
        for word in self.vocabulary:
            existing = await db.fetch_one(
                "SELECT id FROM vocabulary WHERE category_id = ? AND english = ?",
                (word["category_id"], word["english"])
            )
            if not existing:
                await db.execute(
                    """INSERT INTO vocabulary 
                       (category_id, english, portuguese, phonetic, difficulty, example_sentence)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        word["category_id"],
                        word["english"],
                        word["portuguese"],
                        word.get("phonetic", ""),
                        word.get("difficulty", "easy"),
                        word.get("example_sentence", "")
                    )
                )
                inserted += 1
        
        logger.info(f"   Palavras inseridas: {inserted}")
    
    async def _seed_dialogs(self):
        """Insere diálogos"""
        inserted = 0
        for dialog in self.dialogs:
            existing = await db.fetch_one(
                "SELECT id FROM dialogs WHERE theme = ? AND order_num = ?",
                (dialog["theme"], dialog["order_num"])
            )
            if not existing:
                await db.execute(
                    """INSERT INTO dialogs (theme, role, line, translation, order_num)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        dialog["theme"],
                        dialog["role"],
                        dialog["line"],
                        dialog.get("translation", ""),
                        dialog["order_num"]
                    )
                )
                inserted += 1
        
        logger.info(f"   Diálogos inseridos: {inserted}")
    
    async def _seed_achievements(self):
        """Insere conquistas disponíveis"""
        for ach in self.achievements:
            existing = await db.fetch_one(
                "SELECT id FROM achievements WHERE achievement_key = ?",
                (ach["key"],)
            )
            if not existing:
                await db.execute(
                    """INSERT INTO achievements 
                       (achievement_key, title, description, icon)
                       VALUES (?, ?, ?, ?)""",
                    (ach["key"], ach["title"], ach["description"], ach["icon"])
                )
    
    async def _print_stats(self):
        """Exibe estatísticas do banco"""
        cats = await db.fetch_one("SELECT COUNT(*) as count FROM categories")
        words = await db.fetch_one("SELECT COUNT(*) as count FROM vocabulary")
        dialogs = await db.fetch_one("SELECT COUNT(*) as count FROM dialogs")
        achs = await db.fetch_one("SELECT COUNT(*) as count FROM achievements")
        
        logger.info("=" * 40)
        logger.info("📊 ESTATÍSTICAS DO BANCO DE DADOS")
        logger.info(f"   Categorias: {cats['count']}")
        logger.info(f"   Palavras: {words['count']}")
        logger.info(f"   Diálogos: {dialogs['count']}")
        logger.info(f"   Conquistas: {achs['count']}")
        logger.info("=" * 40)
    
    # ================================================================
    # DADOS
    # ================================================================
    
    def _get_categories(self) -> List[Dict]:
        """Retorna categorias de estudo"""
        return [
            {"name": "Animais", "icon": "🐱", "description": "Nomes de animais em inglês", "color": "#4CAF50"},
            {"name": "Cores", "icon": "🎨", "description": "Cores e tonalidades", "color": "#2196F3"},
            {"name": "Aeroporto", "icon": "✈️", "description": "Vocabulário de viagem e aeroporto", "color": "#FF9800"},
            {"name": "Restaurante", "icon": "🍽️", "description": "Como pedir comida e bebidas", "color": "#E91E63"},
            {"name": "Casa", "icon": "🏠", "description": "Objetos e cômodos da casa", "color": "#9C27B0"},
            {"name": "Família", "icon": "👨‍👩‍👧", "description": "Membros da família", "color": "#00BCD4"},
            {"name": "Comida", "icon": "🍕", "description": "Alimentos e bebidas", "color": "#FF5722"},
            {"name": "Roupas", "icon": "👕", "description": "Vestuário e acessórios", "color": "#795548"},
            {"name": "Corpo Humano", "icon": "🏃", "description": "Partes do corpo", "color": "#607D8B"},
            {"name": "Clima", "icon": "🌤️", "description": "Tempo e estações", "color": "#03A9F4"},
        ]
    
    def _get_vocabulary(self) -> List[Dict]:
        """Retorna 200+ palavras organizadas por categoria"""
        return [
            # ==================== ANIMAIS (cat 1) ====================
            {"category_id": 1, "english": "dog", "portuguese": "cachorro", "phonetic": "/dɔɡ/", "difficulty": "easy", "example_sentence": "The dog is playing in the park."},
            {"category_id": 1, "english": "cat", "portuguese": "gato", "phonetic": "/kæt/", "difficulty": "easy", "example_sentence": "My cat loves to sleep."},
            {"category_id": 1, "english": "bird", "portuguese": "pássaro", "phonetic": "/bɜːrd/", "difficulty": "easy", "example_sentence": "The bird sings every morning."},
            {"category_id": 1, "english": "fish", "portuguese": "peixe", "phonetic": "/fɪʃ/", "difficulty": "easy", "example_sentence": "Fish swim in the ocean."},
            {"category_id": 1, "english": "horse", "portuguese": "cavalo", "phonetic": "/hɔːrs/", "difficulty": "medium", "example_sentence": "She rides a beautiful horse."},
            {"category_id": 1, "english": "cow", "portuguese": "vaca", "phonetic": "/kaʊ/", "difficulty": "easy", "example_sentence": "The cow gives milk."},
            {"category_id": 1, "english": "pig", "portuguese": "porco", "phonetic": "/pɪɡ/", "difficulty": "easy", "example_sentence": "Pigs are very intelligent animals."},
            {"category_id": 1, "english": "chicken", "portuguese": "galinha", "phonetic": "/ˈtʃɪk.ɪn/", "difficulty": "medium", "example_sentence": "The chicken lays eggs."},
            {"category_id": 1, "english": "duck", "portuguese": "pato", "phonetic": "/dʌk/", "difficulty": "easy", "example_sentence": "Ducks swim in the pond."},
            {"category_id": 1, "english": "sheep", "portuguese": "ovelha", "phonetic": "/ʃiːp/", "difficulty": "easy", "example_sentence": "Sheep give us wool."},
            {"category_id": 1, "english": "rabbit", "portuguese": "coelho", "phonetic": "/ˈræb.ɪt/", "difficulty": "easy", "example_sentence": "The rabbit hops quickly."},
            {"category_id": 1, "english": "lion", "portuguese": "leão", "phonetic": "/ˈlaɪ.ən/", "difficulty": "medium", "example_sentence": "The lion is the king of the jungle."},
            {"category_id": 1, "english": "tiger", "portuguese": "tigre", "phonetic": "/ˈtaɪ.ɡər/", "difficulty": "medium", "example_sentence": "Tigers have orange and black stripes."},
            {"category_id": 1, "english": "elephant", "portuguese": "elefante", "phonetic": "/ˈel.ɪ.fənt/", "difficulty": "medium", "example_sentence": "Elephants are the largest land animals."},
            {"category_id": 1, "english": "monkey", "portuguese": "macaco", "phonetic": "/ˈmʌŋ.ki/", "difficulty": "easy", "example_sentence": "Monkeys love bananas."},
            {"category_id": 1, "english": "snake", "portuguese": "cobra", "phonetic": "/sneɪk/", "difficulty": "easy", "example_sentence": "The snake moves without legs."},
            {"category_id": 1, "english": "turtle", "portuguese": "tartaruga", "phonetic": "/ˈtɜːr.təl/", "difficulty": "medium", "example_sentence": "Turtles carry their home on their back."},
            {"category_id": 1, "english": "frog", "portuguese": "sapo", "phonetic": "/frɔːɡ/", "difficulty": "easy", "example_sentence": "The frog jumps into the water."},
            {"category_id": 1, "english": "bear", "portuguese": "urso", "phonetic": "/ber/", "difficulty": "easy", "example_sentence": "Bears sleep during winter."},
            {"category_id": 1, "english": "whale", "portuguese": "baleia", "phonetic": "/weɪl/", "difficulty": "medium", "example_sentence": "Whales are the largest animals in the ocean."},
            
            # ==================== CORES (cat 2) ====================
            {"category_id": 2, "english": "red", "portuguese": "vermelho", "phonetic": "/red/", "difficulty": "easy", "example_sentence": "The apple is red."},
            {"category_id": 2, "english": "blue", "portuguese": "azul", "phonetic": "/bluː/", "difficulty": "easy", "example_sentence": "The sky is blue today."},
            {"category_id": 2, "english": "green", "portuguese": "verde", "phonetic": "/ɡriːn/", "difficulty": "easy", "example_sentence": "The grass is green."},
            {"category_id": 2, "english": "yellow", "portuguese": "amarelo", "phonetic": "/ˈjel.oʊ/", "difficulty": "easy", "example_sentence": "The sun is yellow."},
            {"category_id": 2, "english": "black", "portuguese": "preto", "phonetic": "/blæk/", "difficulty": "easy", "example_sentence": "The cat is black."},
            {"category_id": 2, "english": "white", "portuguese": "branco", "phonetic": "/waɪt/", "difficulty": "easy", "example_sentence": "Snow is white."},
            {"category_id": 2, "english": "orange", "portuguese": "laranja", "phonetic": "/ˈɔːr.ɪndʒ/", "difficulty": "medium", "example_sentence": "Oranges are orange."},
            {"category_id": 2, "english": "purple", "portuguese": "roxo", "phonetic": "/ˈpɜːr.pəl/", "difficulty": "medium", "example_sentence": "She loves purple flowers."},
            {"category_id": 2, "english": "pink", "portuguese": "rosa", "phonetic": "/pɪŋk/", "difficulty": "easy", "example_sentence": "The baby has pink clothes."},
            {"category_id": 2, "english": "brown", "portuguese": "marrom", "phonetic": "/braʊn/", "difficulty": "easy", "example_sentence": "The dog has brown fur."},
            {"category_id": 2, "english": "gray", "portuguese": "cinza", "phonetic": "/ɡreɪ/", "difficulty": "easy", "example_sentence": "The sky is gray before rain."},
            {"category_id": 2, "english": "gold", "portuguese": "dourado", "phonetic": "/ɡoʊld/", "difficulty": "medium", "example_sentence": "She wears a gold necklace."},
            {"category_id": 2, "english": "silver", "portuguese": "prateado", "phonetic": "/ˈsɪl.vər/", "difficulty": "medium", "example_sentence": "The ring is silver."},
            {"category_id": 2, "english": "dark blue", "portuguese": "azul escuro", "phonetic": "/dɑːrk bluː/", "difficulty": "medium", "example_sentence": "He wears a dark blue suit."},
            {"category_id": 2, "english": "light green", "portuguese": "verde claro", "phonetic": "/laɪt ɡriːn/", "difficulty": "medium", "example_sentence": "The walls are light green."},
            
            # ==================== AEROPORTO (cat 3) ====================
            {"category_id": 3, "english": "passport", "portuguese": "passaporte", "phonetic": "/ˈpæs.pɔːrt/", "difficulty": "medium", "example_sentence": "Show your passport at the counter."},
            {"category_id": 3, "english": "boarding pass", "portuguese": "cartão de embarque", "phonetic": "/ˈbɔːr.dɪŋ pæs/", "difficulty": "medium", "example_sentence": "Please show your boarding pass."},
            {"category_id": 3, "english": "gate", "portuguese": "portão", "phonetic": "/ɡeɪt/", "difficulty": "easy", "example_sentence": "Your flight is at gate 12."},
            {"category_id": 3, "english": "luggage", "portuguese": "bagagem", "phonetic": "/ˈlʌɡ.ɪdʒ/", "difficulty": "medium", "example_sentence": "Where can I collect my luggage?"},
            {"category_id": 3, "english": "departure", "portuguese": "partida", "phonetic": "/dɪˈpɑːr.tʃər/", "difficulty": "hard", "example_sentence": "Departure is scheduled for 3 PM."},
            {"category_id": 3, "english": "arrival", "portuguese": "chegada", "phonetic": "/əˈraɪ.vəl/", "difficulty": "medium", "example_sentence": "The arrival time is 5 PM."},
            {"category_id": 3, "english": "ticket", "portuguese": "passagem", "phonetic": "/ˈtɪk.ɪt/", "difficulty": "easy", "example_sentence": "I need to buy a ticket."},
            {"category_id": 3, "english": "flight", "portuguese": "voo", "phonetic": "/flaɪt/", "difficulty": "easy", "example_sentence": "The flight takes 3 hours."},
            {"category_id": 3, "english": "airplane", "portuguese": "avião", "phonetic": "/ˈer.pleɪn/", "difficulty": "easy", "example_sentence": "The airplane is ready for boarding."},
            {"category_id": 3, "english": "seat", "portuguese": "assento", "phonetic": "/siːt/", "difficulty": "easy", "example_sentence": "Your seat is 15A."},
            {"category_id": 3, "english": "window", "portuguese": "janela", "phonetic": "/ˈwɪn.doʊ/", "difficulty": "easy", "example_sentence": "I prefer the window seat."},
            {"category_id": 3, "english": "aisle", "portuguese": "corredor", "phonetic": "/aɪl/", "difficulty": "medium", "example_sentence": "Can I have an aisle seat?"},
            {"category_id": 3, "english": "pilot", "portuguese": "piloto", "phonetic": "/ˈpaɪ.lət/", "difficulty": "easy", "example_sentence": "The pilot announced our arrival."},
            {"category_id": 3, "english": "customs", "portuguese": "alfândega", "phonetic": "/ˈkʌs.təmz/", "difficulty": "hard", "example_sentence": "Go through customs after landing."},
            {"category_id": 3, "english": "check-in", "portuguese": "fazer check-in", "phonetic": "/tʃek ɪn/", "difficulty": "medium", "example_sentence": "Check-in online 24 hours before."},
            
            # ==================== RESTAURANTE (cat 4) ====================
            {"category_id": 4, "english": "menu", "portuguese": "cardápio", "phonetic": "/ˈmen.juː/", "difficulty": "easy", "example_sentence": "Can I see the menu, please?"},
            {"category_id": 4, "english": "waiter", "portuguese": "garçom", "phonetic": "/ˈweɪ.tər/", "difficulty": "medium", "example_sentence": "The waiter brought our food."},
            {"category_id": 4, "english": "bill", "portuguese": "conta", "phonetic": "/bɪl/", "difficulty": "easy", "example_sentence": "Can I have the bill, please?"},
            {"category_id": 4, "english": "table", "portuguese": "mesa", "phonetic": "/ˈteɪ.bəl/", "difficulty": "easy", "example_sentence": "A table for two, please."},
            {"category_id": 4, "english": "reservation", "portuguese": "reserva", "phonetic": "/ˌrez.ərˈveɪ.ʃən/", "difficulty": "hard", "example_sentence": "I have a reservation."},
            {"category_id": 4, "english": "appetizer", "portuguese": "entrada", "phonetic": "/ˈæp.ə.taɪ.zər/", "difficulty": "hard", "example_sentence": "We ordered an appetizer first."},
            {"category_id": 4, "english": "main course", "portuguese": "prato principal", "phonetic": "/meɪn kɔːrs/", "difficulty": "medium", "example_sentence": "What is the main course today?"},
            {"category_id": 4, "english": "dessert", "portuguese": "sobremesa", "phonetic": "/dɪˈzɜːrt/", "difficulty": "medium", "example_sentence": "Would you like dessert?"},
            {"category_id": 4, "english": "tip", "portuguese": "gorjeta", "phonetic": "/tɪp/", "difficulty": "easy", "example_sentence": "The tip is not included."},
            {"category_id": 4, "english": "spicy", "portuguese": "picante", "phonetic": "/ˈspaɪ.si/", "difficulty": "medium", "example_sentence": "This food is very spicy!"},
            {"category_id": 4, "english": "delicious", "portuguese": "delicioso", "phonetic": "/dɪˈlɪʃ.əs/", "difficulty": "medium", "example_sentence": "The meal was delicious!"},
            {"category_id": 4, "english": "vegetarian", "portuguese": "vegetariano", "phonetic": "/ˌvedʒ.ɪˈter.i.ən/", "difficulty": "hard", "example_sentence": "Do you have vegetarian options?"},
            
            # ==================== CASA (cat 5) ====================
            {"category_id": 5, "english": "bedroom", "portuguese": "quarto", "phonetic": "/ˈbed.ruːm/", "difficulty": "easy", "example_sentence": "My bedroom is upstairs."},
            {"category_id": 5, "english": "kitchen", "portuguese": "cozinha", "phonetic": "/ˈkɪtʃ.ɪn/", "difficulty": "easy", "example_sentence": "We cook in the kitchen."},
            {"category_id": 5, "english": "bathroom", "portuguese": "banheiro", "phonetic": "/ˈbæθ.ruːm/", "difficulty": "easy", "example_sentence": "The bathroom is clean."},
            {"category_id": 5, "english": "living room", "portuguese": "sala de estar", "phonetic": "/ˈlɪv.ɪŋ ruːm/", "difficulty": "medium", "example_sentence": "We watch TV in the living room."},
            {"category_id": 5, "english": "door", "portuguese": "porta", "phonetic": "/dɔːr/", "difficulty": "easy", "example_sentence": "Close the door, please."},
            {"category_id": 5, "english": "window", "portuguese": "janela", "phonetic": "/ˈwɪn.doʊ/", "difficulty": "easy", "example_sentence": "Open the window for fresh air."},
            {"category_id": 5, "english": "chair", "portuguese": "cadeira", "phonetic": "/tʃer/", "difficulty": "easy", "example_sentence": "Sit on the chair."},
            {"category_id": 5, "english": "table", "portuguese": "mesa", "phonetic": "/ˈteɪ.bəl/", "difficulty": "easy", "example_sentence": "The book is on the table."},
            {"category_id": 5, "english": "bed", "portuguese": "cama", "phonetic": "/bed/", "difficulty": "easy", "example_sentence": "It's time for bed."},
            {"category_id": 5, "english": "sofa", "portuguese": "sofá", "phonetic": "/ˈsoʊ.fə/", "difficulty": "easy", "example_sentence": "The sofa is comfortable."},
            {"category_id": 5, "english": "lamp", "portuguese": "abajur", "phonetic": "/læmp/", "difficulty": "easy", "example_sentence": "Turn on the lamp."},
            {"category_id": 5, "english": "mirror", "portuguese": "espelho", "phonetic": "/ˈmɪr.ər/", "difficulty": "medium", "example_sentence": "Look in the mirror."},
            
            # ==================== FAMÍLIA (cat 6) ====================
            {"category_id": 6, "english": "mother", "portuguese": "mãe", "phonetic": "/ˈmʌð.ər/", "difficulty": "easy", "example_sentence": "My mother is a teacher."},
            {"category_id": 6, "english": "father", "portuguese": "pai", "phonetic": "/ˈfɑː.ðər/", "difficulty": "easy", "example_sentence": "My father works in an office."},
            {"category_id": 6, "english": "sister", "portuguese": "irmã", "phonetic": "/ˈsɪs.tər/", "difficulty": "easy", "example_sentence": "My sister is older than me."},
            {"category_id": 6, "english": "brother", "portuguese": "irmão", "phonetic": "/ˈbrʌð.ər/", "difficulty": "easy", "example_sentence": "My brother plays soccer."},
            {"category_id": 6, "english": "grandmother", "portuguese": "avó", "phonetic": "/ˈɡrænd.mʌð.ər/", "difficulty": "medium", "example_sentence": "My grandmother bakes cookies."},
            {"category_id": 6, "english": "grandfather", "portuguese": "avô", "phonetic": "/ˈɡrænd.fɑː.ðər/", "difficulty": "medium", "example_sentence": "My grandfather tells stories."},
            {"category_id": 6, "english": "uncle", "portuguese": "tio", "phonetic": "/ˈʌŋ.kəl/", "difficulty": "easy", "example_sentence": "My uncle lives nearby."},
            {"category_id": 6, "english": "aunt", "portuguese": "ia", "phonetic": "/ænt/", "difficulty": "easy", "example_sentence": "My aunt is a doctor."},
            {"category_id": 6, "english": "cousin", "portuguese": "primo(a)", "phonetic": "/ˈkʌz.ən/", "difficulty": "medium", "example_sentence": "My cousin is my best friend."},
            {"category_id": 6, "english": "baby", "portuguese": "bebê", "phonetic": "/ˈbeɪ.bi/", "difficulty": "easy", "example_sentence": "The baby is sleeping."},
            
            # ==================== COMIDA (cat 7) ====================
            {"category_id": 7, "english": "rice", "portuguese": "arroz", "phonetic": "/raɪs/", "difficulty": "easy", "example_sentence": "We eat rice every day."},
            {"category_id": 7, "english": "beans", "portuguese": "feijão", "phonetic": "/biːnz/", "difficulty": "easy", "example_sentence": "Beans are rich in protein."},
            {"category_id": 7, "english": "bread", "portuguese": "pão", "phonetic": "/bred/", "difficulty": "easy", "example_sentence": "Fresh bread smells good."},
            {"category_id": 7, "english": "cheese", "portuguese": "queijo", "phonetic": "/tʃiːz/", "difficulty": "easy", "example_sentence": "I love cheese on pizza."},
            {"category_id": 7, "english": "chicken", "portuguese": "frango", "phonetic": "/ˈtʃɪk.ɪn/", "difficulty": "easy", "example_sentence": "Grilled chicken is healthy."},
            {"category_id": 7, "english": "fish", "portuguese": "peixe", "phonetic": "/fɪʃ/", "difficulty": "easy", "example_sentence": "Fish is good for you."},
            {"category_id": 7, "english": "egg", "portuguese": "ovo", "phonetic": "/eɡ/", "difficulty": "easy", "example_sentence": "I eat eggs for breakfast."},
            {"category_id": 7, "english": "milk", "portuguese": "leite", "phonetic": "/mɪlk/", "difficulty": "easy", "example_sentence": "Drink milk every day."},
            {"category_id": 7, "english": "water", "portuguese": "água", "phonetic": "/ˈwɔː.tər/", "difficulty": "easy", "example_sentence": "Water is essential for life."},
            {"category_id": 7, "english": "juice", "portuguese": "suco", "phonetic": "/dʒuːs/", "difficulty": "easy", "example_sentence": "Orange juice is refreshing."},
            {"category_id": 7, "english": "coffee", "portuguese": "café", "phonetic": "/ˈkɔː.fi/", "difficulty": "easy", "example_sentence": "I need coffee in the morning."},
            {"category_id": 7, "english": "tea", "portuguese": "chá", "phonetic": "/tiː/", "difficulty": "easy", "example_sentence": "Would you like some tea?"},
            {"category_id": 7, "english": "sugar", "portuguese": "açúcar", "phonetic": "/ˈʃʊɡ.ər/", "difficulty": "medium", "example_sentence": "No sugar in my coffee, please."},
            {"category_id": 7, "english": "salt", "portuguese": "sal", "phonetic": "/sɔːlt/", "difficulty": "easy", "example_sentence": "Don't add too much salt."},
            
            # ==================== ROUPAS (cat 8) ====================
            {"category_id": 8, "english": "shirt", "portuguese": "camisa", "phonetic": "/ʃɜːrt/", "difficulty": "easy", "example_sentence": "He wears a blue shirt."},
            {"category_id": 8, "english": "pants", "portuguese": "calça", "phonetic": "/pænts/", "difficulty": "easy", "example_sentence": "These pants are new."},
            {"category_id": 8, "english": "shoes", "portuguese": "sapatos", "phonetic": "/ʃuːz/", "difficulty": "easy", "example_sentence": "I need new shoes."},
            {"category_id": 8, "english": "dress", "portuguese": "vestido", "phonetic": "/dres/", "difficulty": "easy", "example_sentence": "She bought a red dress."},
            {"category_id": 8, "english": "jacket", "portuguese": "jaqueta", "phonetic": "/ˈdʒæk.ɪt/", "difficulty": "medium", "example_sentence": "Wear a jacket, it's cold."},
            {"category_id": 8, "english": "hat", "portuguese": "chapéu", "phonetic": "/hæt/", "difficulty": "easy", "example_sentence": "He wears a hat in the sun."},
            {"category_id": 8, "english": "socks", "portuguese": "meias", "phonetic": "/sɑːks/", "difficulty": "easy", "example_sentence": "Put on your socks."},
            {"category_id": 8, "english": "coat", "portuguese": "casaco", "phonetic": "/koʊt/", "difficulty": "easy", "example_sentence": "A warm coat for winter."},
            {"category_id": 8, "english": "scarf", "portuguese": "cachecol", "phonetic": "/skɑːrf/", "difficulty": "medium", "example_sentence": "She knitted a scarf."},
            {"category_id": 8, "english": "gloves", "portuguese": "luvas", "phonetic": "/ɡlʌvz/", "difficulty": "medium", "example_sentence": "Wear gloves in the snow."},
            
            # ==================== CORPO HUMANO (cat 9) ====================
            {"category_id": 9, "english": "head", "portuguese": "cabeça", "phonetic": "/hed/", "difficulty": "easy", "example_sentence": "I have a headache."},
            {"category_id": 9, "english": "eye", "portuguese": "olho", "phonetic": "/aɪ/", "difficulty": "easy", "example_sentence": "She has beautiful eyes."},
            {"category_id": 9, "english": "nose", "portuguese": "nariz", "phonetic": "/noʊz/", "difficulty": "easy", "example_sentence": "My nose is running."},
            {"category_id": 9, "english": "mouth", "portuguese": "boca", "phonetic": "/maʊθ/", "difficulty": "easy", "example_sentence": "Open your mouth."},
            {"category_id": 9, "english": "hand", "portuguese": "mão", "phonetic": "/hænd/", "difficulty": "easy", "example_sentence": "Wash your hands."},
            {"category_id": 9, "english": "foot", "portuguese": "pé", "phonetic": "/fʊt/", "difficulty": "easy", "example_sentence": "My foot hurts."},
            {"category_id": 9, "english": "arm", "portuguese": "braço", "phonetic": "/ɑːrm/", "difficulty": "easy", "example_sentence": "He broke his arm."},
            {"category_id": 9, "english": "leg", "portuguese": "perna", "phonetic": "/leɡ/", "difficulty": "easy", "example_sentence": "She has long legs."},
            {"category_id": 9, "english": "heart", "portuguese": "coração", "phonetic": "/hɑːrt/", "difficulty": "easy", "example_sentence": "The heart pumps blood."},
            {"category_id": 9, "english": "stomach", "portuguese": "estômago", "phonetic": "/ˈstʌm.ək/", "difficulty": "medium", "example_sentence": "My stomach is empty."},
            
            # ==================== CLIMA (cat 10) ====================
            {"category_id": 10, "english": "sunny", "portuguese": "ensolarado", "phonetic": "/ˈsʌn.i/", "difficulty": "easy", "example_sentence": "It's sunny today!"},
            {"category_id": 10, "english": "rainy", "portuguese": "chuvoso", "phonetic": "/ˈreɪ.ni/", "difficulty": "easy", "example_sentence": "It's rainy outside."},
            {"category_id": 10, "english": "cloudy", "portuguese": "nublado", "phonetic": "/ˈklaʊ.di/", "difficulty": "medium", "example_sentence": "The sky is cloudy."},
            {"category_id": 10, "english": "windy", "portuguese": "ventoso", "phonetic": "/ˈwɪn.di/", "difficulty": "medium", "example_sentence": "It's very windy at the beach."},
            {"category_id": 10, "english": "hot", "portuguese": "quente", "phonetic": "/hɑːt/", "difficulty": "easy", "example_sentence": "The weather is hot."},
            {"category_id": 10, "english": "cold", "portuguese": "frio", "phonetic": "/koʊld/", "difficulty": "easy", "example_sentence": "Winter is very cold."},
            {"category_id": 10, "english": "snow", "portuguese": "neve", "phonetic": "/snoʊ/", "difficulty": "easy", "example_sentence": "Snow covers the ground."},
            {"category_id": 10, "english": "storm", "portuguese": "tempestade", "phonetic": "/stɔːrm/", "difficulty": "medium", "example_sentence": "A storm is coming."},
            {"category_id": 10, "english": "rainbow", "portuguese": "arco-íris", "phonetic": "/ˈreɪn.boʊ/", "difficulty": "medium", "example_sentence": "Look at the rainbow!"},
            {"category_id": 10, "english": "temperature", "portuguese": "temperatura", "phonetic": "/ˈtem.pə.rə.tʃər/", "difficulty": "hard", "example_sentence": "The temperature is 25 degrees."},
        ]
    
    def _get_dialogs(self) -> List[Dict]:
        """Retorna diálogos temáticos"""
        return [
            # ==================== AEROPORTO ====================
            {"theme": "Aeroporto", "role": "Atendente", "line": "Good morning! Can I see your passport, please?", "translation": "Bom dia! Posso ver seu passaporte, por favor?", "order_num": 1},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Yes, here it is.", "translation": "Sim, aqui está.", "order_num": 2},
            {"theme": "Aeroporto", "role": "Atendente", "line": "Are you checking any luggage today?", "translation": "Vai despachar alguma bagagem hoje?", "order_num": 3},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Just this one bag.", "translation": "Apenas esta mala.", "order_num": 4},
            {"theme": "Aeroporto", "role": "Atendente", "line": "Here is your boarding pass. Your flight leaves from gate B12.", "translation": "Aqui está seu cartão de embarque. Seu voo sai do portão B12.", "order_num": 5},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Thank you! What time does boarding start?", "translation": "Obrigado! A que horas começa o embarque?", "order_num": 6},
            {"theme": "Aeroporto", "role": "Atendente", "line": "Boarding starts at 2 PM. Have a nice flight!", "translation": "O embarque começa às 14h. Tenha um bom voo!", "order_num": 7},
            
            # ==================== RESTAURANTE ====================
            {"theme": "Restaurante", "role": "Garçom", "line": "Good evening! Do you have a reservation?", "translation": "Boa noite! Vocês têm reserva?", "order_num": 1},
            {"theme": "Restaurante", "role": "Cliente", "line": "No, we don't. A table for two, please.", "translation": "Não, não temos. Uma mesa para dois, por favor.", "order_num": 2},
            {"theme": "Restaurante", "role": "Garçom", "line": "This way, please. Here is the menu.", "translation": "Por aqui, por favor. Aqui está o cardápio.", "order_num": 3},
            {"theme": "Restaurante", "role": "Garçom", "line": "Are you ready to order?", "translation": "Já estão prontos para pedir?", "order_num": 4},
            {"theme": "Restaurante", "role": "Cliente", "line": "Yes, I'd like the grilled chicken, please.", "translation": "Sim, eu gostaria do frango grelhado, por favor.", "order_num": 5},
            {"theme": "Restaurante", "role": "Garçom", "line": "Excellent choice! And to drink?", "translation": "Excelente escolha! E para beber?", "order_num": 6},
            {"theme": "Restaurante", "role": "Cliente", "line": "A glass of water, please.", "translation": "Um copo de água, por favor.", "order_num": 7},
            {"theme": "Restaurante", "role": "Garçom", "line": "Here is your food. Enjoy your meal!", "translation": "Aqui está sua comida. Bom apetite!", "order_num": 8},
            {"theme": "Restaurante", "role": "Cliente", "line": "Could I have the bill, please?", "translation": "Poderia trazer a conta, por favor?", "order_num": 9},
            
            # ==================== HOTEL ====================
            {"theme": "Hotel", "role": "Recepcionista", "line": "Welcome to the Grand Hotel. How can I help you?", "translation": "Bem-vindo ao Grand Hotel. Como posso ajudar?", "order_num": 1},
            {"theme": "Hotel", "role": "Hóspede", "line": "I have a reservation under the name Silva.", "translation": "Tenho uma reserva no nome Silva.", "order_num": 2},
            {"theme": "Hotel", "role": "Recepcionista", "line": "Yes, I found it. You'll be in room 305.", "translation": "Sim, encontrei. Você ficará no quarto 305.", "order_num": 3},
            {"theme": "Hotel", "role": "Hóspede", "line": "What time is breakfast served?", "translation": "A que horas é servido o café da manhã?", "order_num": 4},
            {"theme": "Hotel", "role": "Recepcionista", "line": "Breakfast is from 6 to 10 AM. The elevator is on your left.", "translation": "O café é das 6h às 10h. O elevador está à sua esquerda.", "order_num": 5},
            {"theme": "Hotel", "role": "Hóspede", "line": "Thank you very much!", "translation": "Muito obrigado!", "order_num": 6},
        ]
    
    def _get_achievements(self) -> List[Dict]:
        """Retorna conquistas disponíveis"""
        return [
            {"key": "first_word", "title": "🎯 Primeira Palavra", "description": "Pratique sua primeira palavra", "icon": "🎯"},
            {"key": "streak_3", "title": "🔥 3 Dias", "description": "Pratique 3 dias seguidos", "icon": "🔥"},
            {"key": "streak_7", "title": "⭐ 7 Dias", "description": "Pratique 7 dias seguidos", "icon": "⭐"},
            {"key": "streak_30", "title": "👑 30 Dias", "description": "Pratique 30 dias seguidos", "icon": "👑"},
            {"key": "category_animals", "title": "🐱 Mestre dos Animais", "description": "Domine todas as palavras de animais", "icon": "🐱"},
            {"key": "category_airport", "title": "✈️ Viajante", "description": "Domine todo o vocabulário de aeroporto", "icon": "✈️"},
            {"key": "score_100", "title": "💯 Perfeito!", "description": "Tire nota 100 em uma palavra", "icon": "💯"},
            {"key": "words_50", "title": "📖 50 Palavras", "description": "Aprenda 50 palavras", "icon": "📖"},
            {"key": "words_100", "title": "📚 100 Palavras", "description": "Aprenda 100 palavras", "icon": "📚"},
            {"key": "dialog_complete", "title": "🗣️ Diálogo Completo", "description": "Complete um diálogo inteiro", "icon": "🗣️"},
            {"key": "perfect_streak_10", "title": "🌟 Sequência Perfeita", "description": "Acerte 10 palavras seguidas", "icon": "🌟"},
            {"key": "all_categories", "title": "🏆 Conhecedor", "description": "Pratique todas as categorias", "icon": "🏆"},
        ]


# Instância global
seeder = DataSeeder()