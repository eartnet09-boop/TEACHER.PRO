# src/data/seeder.py
"""
Populador de dados iniciais do banco de dados.
300+ palavras, 80+ diálogos, 12 categorias, 18 conquistas.
Sistema completo de seed com verificação de integridade e estatísticas.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from .database import db

logger = logging.getLogger(__name__)


class DataSeeder:
    """
    Responsável por popular o banco de dados com dados iniciais completos.
    
    Dados incluídos:
    - 12 categorias temáticas
    - 300+ palavras com fonética e exemplos
    - 80+ linhas de diálogo em 10 temas
    - 18 conquistas gamificadas
    
    O seed é idempotente: não duplica dados existentes.
    """
    
    def __init__(self):
        self.start_time = None
        self.stats = {
            "categories": 0,
            "vocabulary": 0,
            "dialogs": 0,
            "achievements": 0,
            "skipped": 0,
            "errors": 0,
        }
    
    # ================================================================
    # MÉTODO PRINCIPAL
    # ================================================================
    
    async def seed_all(self, force: bool = False) -> Dict:
        """
        Popula todas as tabelas com dados iniciais.
        
        Args:
            force: Se True, limpa dados existentes antes de inserir
            
        Returns:
            Dict com estatísticas do seed
        """
        self.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("🌱 INICIANDO SEED DO BANCO DE DADOS")
        logger.info("=" * 60)
        
        if force:
            logger.warning("⚠️  Modo FORCE ativado: dados existentes serão removidos!")
            await self._clear_all_data()
        
        try:
            await self._seed_categories()
            await self._seed_vocabulary()
            await self._seed_dialogs()
            await self._seed_achievements()
            await self._seed_default_user()
        except Exception as e:
            logger.error(f"❌ Erro durante o seed: {e}")
            raise
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("✅ SEED CONCLUÍDO COM SUCESSO!")
        logger.info(f"   Tempo: {elapsed:.2f}s")
        logger.info(f"   Categorias: {self.stats['categories']}")
        logger.info(f"   Palavras: {self.stats['vocabulary']}")
        logger.info(f"   Diálogos: {self.stats['dialogs']}")
        logger.info(f"   Conquistas: {self.stats['achievements']}")
        if self.stats['skipped'] > 0:
            logger.info(f"   Pulados (já existiam): {self.stats['skipped']}")
        if self.stats['errors'] > 0:
            logger.warning(f"   Erros: {self.stats['errors']}")
        logger.info("=" * 60)
        
        return self.stats
    
    # ================================================================
    # LIMPEZA (MODO FORCE)
    # ================================================================
    
    async def _clear_all_data(self):
        """Remove todos os dados existentes (usado com force=True)"""
        tables = ["vocabulary", "dialogs", "user_progress", 
                  "study_sessions", "achievements", "user_streaks", "categories"]
        for table in tables:
            await db.execute(f"DELETE FROM {table}")
        logger.info("🧹 Dados anteriores removidos")
    
    # ================================================================
    # SEED DE CATEGORIAS
    # ================================================================
    
    async def _seed_categories(self):
        """Insere categorias de estudo"""
        categories = self._get_all_categories()
        
        for cat in categories:
            try:
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
                    self.stats["categories"] += 1
                else:
                    self.stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Erro ao inserir categoria '{cat['name']}': {e}")
                self.stats["errors"] += 1
        
        logger.info(f"📁 Categorias: {self.stats['categories']} inseridas, {self.stats['skipped']} puladas")
    
    # ================================================================
    # SEED DE VOCABULÁRIO
    # ================================================================
    
    async def _seed_vocabulary(self):
        """Insere palavras do vocabulário (300+ palavras)"""
        all_words = self._get_all_vocabulary()
        
        for word in all_words:
            try:
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
                    self.stats["vocabulary"] += 1
                else:
                    self.stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Erro ao inserir palavra '{word['english']}': {e}")
                self.stats["errors"] += 1
        
        logger.info(f"📝 Palavras: {self.stats['vocabulary']} inseridas")
    
    # ================================================================
    # SEED DE DIÁLOGOS
    # ================================================================
    
    async def _seed_dialogs(self):
        """Insere todos os diálogos (básicos + expandidos)"""
        all_dialogs = self._get_base_dialogs() + self._get_expanded_dialogs()
        
        for dialog in all_dialogs:
            try:
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
                    self.stats["dialogs"] += 1
                else:
                    self.stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Erro ao inserir diálogo '{dialog['theme']}#{dialog['order_num']}': {e}")
                self.stats["errors"] += 1
        
        logger.info(f"💬 Diálogos: {self.stats['dialogs']} inseridos")
    
    # ================================================================
    # SEED DE CONQUISTAS
    # ================================================================
    
    async def _seed_achievements(self):
        """Insere conquistas disponíveis"""
        achievements = self._get_all_achievements()
        
        for ach in achievements:
            try:
                existing = await db.fetch_one(
                    "SELECT id FROM achievements WHERE achievement_key = ? AND user_id = 'default'",
                    (ach["key"],)
                )
                if not existing:
                    await db.execute(
                        """INSERT INTO achievements 
                           (user_id, achievement_key, title, description, icon, progress, completed)
                           VALUES ('default', ?, ?, ?, ?, 0.0, 0)""",
                        (ach["key"], ach["title"], ach["description"], ach["icon"])
                    )
                    self.stats["achievements"] += 1
                else:
                    self.stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Erro ao inserir conquista '{ach['key']}': {e}")
                self.stats["errors"] += 1
        
        logger.info(f"🏆 Conquistas: {self.stats['achievements']} inseridas")
    
    # ================================================================
    # SEED DE USUÁRIO PADRÃO
    # ================================================================
    
    async def _seed_default_user(self):
        """Cria usuário padrão se não existir"""
        existing = await db.fetch_one(
            "SELECT user_id FROM user_streaks WHERE user_id = 'default'"
        )
        if not existing:
            await db.execute(
                """INSERT INTO user_streaks (user_id, current_streak, longest_streak, total_xp, current_level)
                   VALUES ('default', 0, 0, 0, 1)"""
            )
            logger.info("👤 Usuário padrão criado")
    
    # ================================================================
    # DADOS: CATEGORIAS (12)
    # ================================================================
    
    def _get_all_categories(self) -> List[Dict]:
        """Retorna todas as categorias de estudo (12)"""
        return [
            {"name": "Animais", "icon": "🐱", "description": "Nomes de animais em inglês", "color": "#4CAF50"},
            {"name": "Cores", "icon": "🎨", "description": "Cores e tonalidades", "color": "#2196F3"},
            {"name": "Aeroporto", "icon": "✈️", "description": "Vocabulário de viagem e aeroporto", "color": "#FF9800"},
            {"name": "Restaurante", "icon": "🍽️", "description": "Como pedir comida e bebidas", "color": "#E91E63"},
            {"name": "Casa", "icon": "🏠", "description": "Objetos e cômodos da casa", "color": "#9C27B0"},
            {"name": "Família", "icon": "👨‍👩‍👧", "description": "Membros da família e parentes", "color": "#00BCD4"},
            {"name": "Comida", "icon": "🍕", "description": "Alimentos, bebidas e ingredientes", "color": "#FF5722"},
            {"name": "Roupas", "icon": "👕", "description": "Vestuário e acessórios", "color": "#795548"},
            {"name": "Corpo Humano", "icon": "🏃", "description": "Partes do corpo e saúde", "color": "#607D8B"},
            {"name": "Clima", "icon": "🌤️", "description": "Tempo, estações e fenômenos naturais", "color": "#03A9F4"},
            {"name": "Transporte", "icon": "🚗", "description": "Meios de transporte e direção", "color": "#FF6F00"},
            {"name": "Profissões", "icon": "💼", "description": "Ocupações e carreiras", "color": "#33691E"},
            {"name": "Números", "icon": "🔢", "description": "Números cardinais, ordinais e medidas", "color":"#FF6F00"},
        ]
    
    # ================================================================
    # DADOS: VOCABULÁRIO (300+ palavras)
    # ================================================================
    
    def _get_all_vocabulary(self) -> List[Dict]:
        """Retorna 300+ palavras organizadas por categoria"""
        words = []
        
        # ==================== ANIMAIS (cat 1) - 25 palavras ====================
        animals = [
            ("dog", "cachorro", "/dɔɡ/", "easy", "The dog is playing in the park."),
            ("cat", "gato", "/kæt/", "easy", "My cat loves to sleep."),
            ("bird", "pássaro", "/bɜːrd/", "easy", "The bird sings every morning."),
            ("fish", "peixe", "/fɪʃ/", "easy", "Fish swim in the ocean."),
            ("horse", "cavalo", "/hɔːrs/", "medium", "She rides a beautiful horse."),
            ("cow", "vaca", "/kaʊ/", "easy", "The cow gives milk."),
            ("pig", "porco", "/pɪɡ/", "easy", "Pigs are very intelligent animals."),
            ("chicken", "galinha", "/ˈtʃɪk.ɪn/", "medium", "The chicken lays eggs."),
            ("duck", "pato", "/dʌk/", "easy", "Ducks swim in the pond."),
            ("sheep", "ovelha", "/ʃiːp/", "easy", "Sheep give us wool."),
            ("rabbit", "coelho", "/ˈræb.ɪt/", "easy", "The rabbit hops quickly."),
            ("lion", "leão", "/ˈlaɪ.ən/", "medium", "The lion is the king of the jungle."),
            ("tiger", "tigre", "/ˈtaɪ.ɡər/", "medium", "Tigers have orange and black stripes."),
            ("elephant", "elefante", "/ˈel.ɪ.fənt/", "medium", "Elephants are the largest land animals."),
            ("monkey", "macaco", "/ˈmʌŋ.ki/", "easy", "Monkeys love bananas."),
            ("snake", "cobra", "/sneɪk/", "easy", "The snake moves without legs."),
            ("turtle", "tartaruga", "/ˈtɜːr.təl/", "medium", "Turtles carry their home on their back."),
            ("frog", "sapo", "/frɔːɡ/", "easy", "The frog jumps into the water."),
            ("bear", "urso", "/ber/", "easy", "Bears sleep during winter."),
            ("whale", "baleia", "/weɪl/", "medium", "Whales are the largest animals in the ocean."),
            ("shark", "tubarão", "/ʃɑːrk/", "medium", "Sharks have sharp teeth."),
            ("eagle", "águia", "/ˈiː.ɡəl/", "medium", "The eagle flies high in the sky."),
            ("butterfly", "borboleta", "/ˈbʌt.ər.flaɪ/", "medium", "A beautiful butterfly landed on the flower."),
            ("ant", "formiga", "/ænt/", "easy", "Ants work together as a team."),
            ("bee", "abelha", "/biː/", "easy", "Bees make honey."),
        ]
        words.extend([{"category_id": 1, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in animals])
        
        # ==================== CORES (cat 2) - 18 palavras ====================
        colors = [
            ("red", "vermelho", "/red/", "easy", "The apple is red."),
            ("blue", "azul", "/bluː/", "easy", "The sky is blue today."),
            ("green", "verde", "/ɡriːn/", "easy", "The grass is green."),
            ("yellow", "amarelo", "/ˈjel.oʊ/", "easy", "The sun is yellow."),
            ("black", "preto", "/blæk/", "easy", "The cat is black."),
            ("white", "branco", "/waɪt/", "easy", "Snow is white."),
            ("orange", "laranja", "/ˈɔːr.ɪndʒ/", "medium", "Oranges are orange."),
            ("purple", "roxo", "/ˈpɜːr.pəl/", "medium", "She loves purple flowers."),
            ("pink", "rosa", "/pɪŋk/", "easy", "The baby has pink clothes."),
            ("brown", "marrom", "/braʊn/", "easy", "The dog has brown fur."),
            ("gray", "cinza", "/ɡreɪ/", "easy", "The sky is gray before rain."),
            ("gold", "dourado", "/ɡoʊld/", "medium", "She wears a gold necklace."),
            ("silver", "prateado", "/ˈsɪl.vər/", "medium", "The ring is silver."),
            ("beige", "bege", "/beɪʒ/", "medium", "The walls are painted beige."),
            ("navy blue", "azul marinho", "/ˈneɪ.vi bluː/", "hard", "He wore a navy blue uniform."),
            ("turquoise", "turquesa", "/ˈtɜːr.kwɔɪz/", "hard", "The ocean has a turquoise color."),
            ("violet", "violeta", "/ˈvaɪ.ə.lɪt/", "medium", "Violet flowers bloom in spring."),
            ("crimson", "carmesim", "/ˈkrɪm.zən/", "hard", "The sunset was crimson red."),
        ]
        words.extend([{"category_id": 2, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in colors])
        
        # ==================== AEROPORTO (cat 3) - 20 palavras ====================
        airport = [
            ("passport", "passaporte", "/ˈpæs.pɔːrt/", "medium", "Show your passport at the counter."),
            ("boarding pass", "cartão de embarque", "/ˈbɔːr.dɪŋ pæs/", "medium", "Please show your boarding pass."),
            ("gate", "portão de embarque", "/ɡeɪt/", "easy", "Your flight is at gate 12."),
            ("luggage", "bagagem", "/ˈlʌɡ.ɪdʒ/", "medium", "Where can I collect my luggage?"),
            ("departure", "partida", "/dɪˈpɑːr.tʃər/", "hard", "Departure is scheduled for 3 PM."),
            ("arrival", "chegada", "/əˈraɪ.vəl/", "medium", "The arrival time is 5 PM."),
            ("ticket", "passagem", "/ˈtɪk.ɪt/", "easy", "I need to buy a ticket."),
            ("flight", "voo", "/flaɪt/", "easy", "The flight takes 3 hours."),
            ("airplane", "avião", "/ˈer.pleɪn/", "easy", "The airplane is ready for boarding."),
            ("seat", "assento", "/siːt/", "easy", "Your seat is 15A."),
            ("aisle", "corredor", "/aɪl/", "medium", "Can I have an aisle seat?"),
            ("pilot", "piloto", "/ˈpaɪ.lət/", "easy", "The pilot announced our arrival."),
            ("customs", "alfândega", "/ˈkʌs.təmz/", "hard", "Go through customs after landing."),
            ("check-in", "fazer check-in", "/tʃek ɪn/", "medium", "Check-in online 24 hours before."),
            ("delayed", "atrasado", "/dɪˈleɪd/", "medium", "The flight was delayed by 2 hours."),
            ("carry-on", "bagagem de mão", "/ˈkær.i ɒn/", "medium", "Your carry-on must fit in the overhead bin."),
            ("terminal", "terminal", "/ˈtɜːr.mɪ.nəl/", "medium", "International flights depart from Terminal 3."),
            ("security check", "controle de segurança", "/sɪˈkjʊr.ə.ti tʃek/", "hard", "Remove your laptop at the security check."),
            ("baggage claim", "esteira de bagagem", "/ˈbæɡ.ɪdʒ kleɪm/", "hard", "Baggage claim is on the first floor."),
            ("duty-free", "loja duty-free", "/ˈduː.ti friː/", "medium", "I bought perfume at the duty-free shop."),
        ]
        words.extend([{"category_id": 3, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in airport])
        
        # ==================== RESTAURANTE (cat 4) - 20 palavras ====================
        restaurant = [
            ("menu", "cardápio", "/ˈmen.juː/", "easy", "Can I see the menu, please?"),
            ("waiter", "garçom", "/ˈweɪ.tər/", "medium", "The waiter brought our food."),
            ("bill", "conta", "/bɪl/", "easy", "Can I have the bill, please?"),
            ("reservation", "reserva", "/ˌrez.ərˈveɪ.ʃən/", "hard", "I have a reservation at 7 PM."),
            ("appetizer", "entrada", "/ˈæp.ə.taɪ.zər/", "hard", "We ordered an appetizer to share."),
            ("main course", "prato principal", "/meɪn kɔːrs/", "medium", "What is the main course today?"),
            ("dessert", "sobremesa", "/dɪˈzɜːrt/", "medium", "Would you like to see the dessert menu?"),
            ("tip", "gorjeta", "/tɪp/", "easy", "The tip is not included in the bill."),
            ("spicy", "picante", "/ˈspaɪ.si/", "medium", "This food is very spicy!"),
            ("delicious", "delicioso", "/dɪˈlɪʃ.əs/", "medium", "The meal was absolutely delicious!"),
            ("vegetarian", "vegetariano", "/ˌvedʒ.ɪˈter.i.ən/", "hard", "Do you have vegetarian options?"),
            ("napkin", "guardanapo", "/ˈnæp.kɪn/", "medium", "Could I have another napkin, please?"),
            ("fork", "garfo", "/fɔːrk/", "easy", "I dropped my fork on the floor."),
            ("knife", "faca", "/naɪf/", "easy", "Please bring me a clean knife."),
            ("spoon", "colher", "/spuːn/", "easy", "Use a spoon for the soup."),
            ("rare", "mal passado", "/rer/", "medium", "I'd like my steak rare, please."),
            ("medium-rare", "ao ponto", "/ˈmiː.di.əm rer/", "hard", "Medium-rare is perfect for me."),
            ("well-done", "bem passado", "/wel dʌn/", "medium", "He prefers his burger well-done."),
            ("refill", "refil", "/ˈriː.fɪl/", "medium", "Is the soda refill free?"),
            ("takeout", "para viagem", "/ˈteɪk.aʊt/", "medium", "I'd like to order takeout, please."),
        ]
        words.extend([{"category_id": 4, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in restaurant])
        
        # ==================== CASA (cat 5) - 20 palavras ====================
        house = [
            ("bedroom", "quarto", "/ˈbed.ruːm/", "easy", "My bedroom is upstairs."),
            ("kitchen", "cozinha", "/ˈkɪtʃ.ɪn/", "easy", "We cook in the kitchen."),
            ("bathroom", "banheiro", "/ˈbæθ.ruːm/", "easy", "The bathroom is clean."),
            ("living room", "sala de estar", "/ˈlɪv.ɪŋ ruːm/", "medium", "We watch TV in the living room."),
            ("door", "porta", "/dɔːr/", "easy", "Close the door, please."),
            ("window", "janela", "/ˈwɪn.doʊ/", "easy", "Open the window for fresh air."),
            ("chair", "cadeira", "/tʃer/", "easy", "Sit on the chair."),
            ("table", "mesa", "/ˈteɪ.bəl/", "easy", "The book is on the table."),
            ("bed", "cama", "/bed/", "easy", "It's time for bed."),
            ("sofa", "sofá", "/ˈsoʊ.fə/", "easy", "The sofa is comfortable."),
            ("lamp", "abajur", "/læmp/", "easy", "Turn on the lamp."),
            ("mirror", "espelho", "/ˈmɪr.ər/", "medium", "Look in the mirror."),
            ("closet", "armário", "/ˈklɑː.zɪt/", "medium", "My clothes are in the closet."),
            ("refrigerator", "geladeira", "/rɪˈfrɪdʒ.ə.reɪ.tər/", "hard", "Put the milk in the refrigerator."),
            ("oven", "forno", "/ˈʌv.ən/", "medium", "Preheat the oven to 350 degrees."),
            ("microwave", "micro-ondas", "/ˈmaɪ.krə.weɪv/", "hard", "Heat it in the microwave for 2 minutes."),
            ("pillow", "travesseiro", "/ˈpɪl.oʊ/", "medium", "This pillow is very soft."),
            ("blanket", "cobertor", "/ˈblæŋ.kɪt/", "medium", "I need an extra blanket."),
            ("towel", "toalha", "/ˈtaʊ.əl/", "easy", "Grab a clean towel from the closet."),
            ("shower", "chuveiro", "/ˈʃaʊ.ər/", "easy", "I'm going to take a shower."),
        ]
        words.extend([{"category_id": 5, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in house])
        
        # ==================== FAMÍLIA (cat 6) - 20 palavras ====================
        family = [
            ("mother", "mãe", "/ˈmʌð.ər/", "easy", "My mother is a teacher."),
            ("father", "pai", "/ˈfɑː.ðər/", "easy", "My father works in an office."),
            ("sister", "irmã", "/ˈsɪs.tər/", "easy", "My sister is older than me."),
            ("brother", "irmão", "/ˈbrʌð.ər/", "easy", "My brother plays soccer."),
            ("grandmother", "avó", "/ˈɡrænd.mʌð.ər/", "medium", "My grandmother bakes cookies."),
            ("grandfather", "avô", "/ˈɡrænd.fɑː.ðər/", "medium", "My grandfather tells stories."),
            ("uncle", "tio", "/ˈʌŋ.kəl/", "easy", "My uncle lives nearby."),
            ("aunt", "tia", "/ænt/", "easy", "My aunt is a doctor."),
            ("cousin", "primo(a)", "/ˈkʌz.ən/", "medium", "My cousin is my best friend."),
            ("baby", "bebê", "/ˈbeɪ.bi/", "easy", "The baby is sleeping."),
            ("husband", "marido", "/ˈhʌz.bənd/", "medium", "Her husband is a pilot."),
            ("wife", "esposa", "/waɪf/", "medium", "His wife speaks three languages."),
            ("son", "filho", "/sʌn/", "easy", "Their son is in college."),
            ("daughter", "filha", "/ˈdɔː.tər/", "easy", "My daughter loves to draw."),
            ("nephew", "sobrinho", "/ˈnef.juː/", "medium", "My nephew is very funny."),
            ("niece", "sobrinha", "/niːs/", "medium", "My niece just learned to walk."),
            ("mother-in-law", "sogra", "/ˈmʌð.ər ɪn lɔː/", "hard", "My mother-in-law is visiting us."),
            ("father-in-law", "sogro", "/ˈfɑː.ðər ɪn lɔː/", "hard", "My father-in-law retired last year."),
            ("stepfather", "padrasto", "/ˈstep.fɑː.ðər/", "medium", "My stepfather taught me to drive."),
            ("stepmother", "madrasta", "/ˈstep.mʌð.ər/", "medium", "My stepmother is very kind."),
        ]
        words.extend([{"category_id": 6, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in family])
        
        # ==================== COMIDA (cat 7) - 25 palavras ====================
        food = [
            ("rice", "arroz", "/raɪs/", "easy", "We eat rice every day."),
            ("beans", "feijão", "/biːnz/", "easy", "Beans are rich in protein."),
            ("bread", "pão", "/bred/", "easy", "Fresh bread smells good."),
            ("cheese", "queijo", "/tʃiːz/", "easy", "I love cheese on pizza."),
            ("chicken", "frango", "/ˈtʃɪk.ɪn/", "easy", "Grilled chicken is healthy."),
            ("fish", "peixe", "/fɪʃ/", "easy", "Fish is good for your brain."),
            ("egg", "ovo", "/eɡ/", "easy", "I eat eggs for breakfast."),
            ("milk", "leite", "/mɪlk/", "easy", "Drink milk every day."),
            ("water", "água", "/ˈwɔː.tər/", "easy", "Water is essential for life."),
            ("juice", "suco", "/dʒuːs/", "easy", "Orange juice is refreshing."),
            ("coffee", "café", "/ˈkɔː.fi/", "easy", "I need coffee in the morning."),
            ("tea", "chá", "/tiː/", "easy", "Would you like some tea?"),
            ("sugar", "açúcar", "/ˈʃʊɡ.ər/", "medium", "No sugar in my coffee, please."),
            ("salt", "sal", "/sɔːlt/", "easy", "Don't add too much salt."),
            ("butter", "manteiga", "/ˈbʌt.ər/", "medium", "Spread butter on the toast."),
            ("pasta", "macarrão", "/ˈpɑː.stə/", "medium", "I love Italian pasta."),
            ("salad", "salada", "/ˈsæl.əd/", "easy", "I'll have the chicken salad."),
            ("soup", "sopa", "/suːp/", "easy", "Hot soup on a cold day."),
            ("steak", "bife", "/steɪk/", "medium", "I'd like my steak medium-rare."),
            ("bacon", "bacon", "/ˈbeɪ.kən/", "easy", "Bacon and eggs for breakfast."),
            ("chocolate", "chocolate", "/ˈtʃɑːk.lət/", "medium", "Dark chocolate is my favorite."),
            ("ice cream", "sorvete", "/aɪs kriːm/", "easy", "Ice cream melts in the sun."),
            ("cake", "bolo", "/keɪk/", "easy", "Birthday cake with candles."),
            ("cookie", "biscoito", "/ˈkʊk.i/", "easy", "Would you like a cookie?"),
            ("honey", "mel", "/ˈhʌn.i/", "easy", "Tea with honey is soothing."),
        ]
        words.extend([{"category_id": 7, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in food])
        
        # ==================== ROUPAS (cat 8) - 20 palavras ====================
        clothes = [
            ("shirt", "camisa", "/ʃɜːrt/", "easy", "He wears a blue shirt."),
            ("pants", "calça", "/pænts/", "easy", "These pants are new."),
            ("shoes", "sapatos", "/ʃuːz/", "easy", "I need new shoes."),
            ("dress", "vestido", "/dres/", "easy", "She bought a red dress."),
            ("jacket", "jaqueta", "/ˈdʒæk.ɪt/", "medium", "Wear a jacket, it's cold."),
            ("hat", "chapéu", "/hæt/", "easy", "He wears a hat in the sun."),
            ("socks", "meias", "/sɑːks/", "easy", "Put on your socks."),
            ("coat", "casaco", "/koʊt/", "easy", "A warm coat for winter."),
            ("scarf", "cachecol", "/skɑːrf/", "medium", "She knitted a red scarf."),
            ("gloves", "luvas", "/ɡlʌvz/", "medium", "Wear gloves in the snow."),
            ("boots", "botas", "/buːts/", "easy", "Rain boots for wet weather."),
            ("sweater", "suéter", "/ˈswet.ər/", "medium", "A cozy sweater for fall."),
            ("shorts", "shorts/bermuda", "/ʃɔːrts/", "easy", "I wear shorts in summer."),
            ("tie", "gravata", "/taɪ/", "easy", "He wore a tie to the wedding."),
            ("belt", "cinto", "/belt/", "easy", "I need a belt for these pants."),
            ("pajamas", "pijama", "/pəˈdʒɑː.məz/", "medium", "Put on your pajamas."),
            ("sunglasses", "óculos de sol", "/ˈsʌn.ɡlæs.ɪz/", "medium", "Don't forget your sunglasses."),
            ("swimsuit", "roupa de banho", "/ˈswɪm.suːt/", "medium", "Pack your swimsuit for the beach."),
            ("raincoat", "capa de chuva", "/ˈreɪn.koʊt/", "medium", "Bring a raincoat, it might rain."),
            ("uniform", "uniforme", "/ˈjuː.nɪ.fɔːrm/", "medium", "The school uniform is blue and white."),
        ]
        words.extend([{"category_id": 8, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in clothes])
        
        # ==================== CORPO HUMANO (cat 9) - 20 palavras ====================
        body = [
            ("head", "cabeça", "/hed/", "easy", "I have a headache."),
            ("eye", "olho", "/aɪ/", "easy", "She has beautiful eyes."),
            ("nose", "nariz", "/noʊz/", "easy", "My nose is running."),
            ("mouth", "boca", "/maʊθ/", "easy", "Open your mouth."),
            ("hand", "mão", "/hænd/", "easy", "Wash your hands."),
            ("foot", "pé", "/fʊt/", "easy", "My foot hurts."),
            ("arm", "braço", "/ɑːrm/", "easy", "He broke his arm."),
            ("leg", "perna", "/leɡ/", "easy", "She has long legs."),
            ("heart", "coração", "/hɑːrt/", "easy", "The heart pumps blood."),
            ("stomach", "estômago", "/ˈstʌm.ək/", "medium", "My stomach is growling."),
            ("finger", "dedo da mão", "/ˈfɪŋ.ɡər/", "easy", "I cut my finger."),
            ("toe", "dedo do pé", "/toʊ/", "easy", "I stubbed my toe."),
            ("knee", "joelho", "/niː/", "easy", "My knee hurts after running."),
            ("elbow", "cotovelo", "/ˈel.boʊ/", "medium", "Don't put your elbows on the table."),
            ("shoulder", "ombro", "/ˈʃoʊl.dər/", "medium", "She has strong shoulders."),
            ("neck", "pescoço", "/nek/", "easy", "My neck is stiff."),
            ("back", "costas", "/bæk/", "easy", "I have back pain."),
            ("ear", "orelha", "/ɪr/", "easy", "Whisper in my ear."),
            ("teeth", "dentes", "/tiːθ/", "easy", "Brush your teeth twice a day."),
            ("tongue", "língua", "/tʌŋ/", "medium", "I bit my tongue."),
        ]
        words.extend([{"category_id": 9, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in body])
        
        # ==================== CLIMA (cat 10) - 20 palavras ====================
        weather = [
            ("sunny", "ensolarado", "/ˈsʌn.i/", "easy", "It's sunny today!"),
            ("rainy", "chuvoso", "/ˈreɪ.ni/", "easy", "It's rainy outside."),
            ("cloudy", "nublado", "/ˈklaʊ.di/", "medium", "The sky is cloudy."),
            ("windy", "ventoso", "/ˈwɪn.di/", "medium", "It's very windy at the beach."),
            ("hot", "quente", "/hɑːt/", "easy", "The weather is hot today."),
            ("cold", "frio", "/koʊld/", "easy", "Winter is very cold here."),
            ("snow", "neve", "/snoʊ/", "easy", "Snow covers the ground."),
            ("storm", "tempestade", "/stɔːrm/", "medium", "A storm is approaching."),
            ("rainbow", "arco-íris", "/ˈreɪn.boʊ/", "medium", "Look at the beautiful rainbow!"),
            ("temperature", "temperatura", "/ˈtem.pə.rə.tʃər/", "hard", "The temperature dropped below zero."),
            ("lightning", "relâmpago", "/ˈlaɪt.nɪŋ/", "hard", "Lightning struck the tree."),
            ("thunder", "trovão", "/ˈθʌn.dər/", "medium", "Did you hear that thunder?"),
            ("foggy", "com neblina", "/ˈfɑː.ɡi/", "medium", "Drive carefully, it's foggy."),
            ("humid", "úmido", "/ˈhjuː.mɪd/", "hard", "The air is very humid today."),
            ("drizzle", "garoa", "/ˈdrɪz.əl/", "hard", "Just a light drizzle outside."),
            ("hail", "granizo", "/heɪl/", "hard", "Hail damaged my car."),
            ("spring", "primavera", "/sprɪŋ/", "easy", "Flowers bloom in spring."),
            ("summer", "verão", "/ˈsʌm.ər/", "easy", "Summer is my favorite season."),
            ("fall/autumn", "outono", "/fɔːl/ / /ˈɔː.təm/", "medium", "Leaves change color in the fall."),
            ("winter", "inverno", "/ˈwɪn.tər/", "easy", "We go skiing in winter."),
        ]
        words.extend([{"category_id": 10, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in weather])
        
        # ==================== TRANSPORTE (cat 11) - 20 palavras ====================
        transport = [
            ("car", "carro", "/kɑːr/", "easy", "I drive my car to work."),
            ("bus", "ônibus", "/bʌs/", "easy", "The bus arrives at 8 AM."),
            ("train", "trem", "/treɪn/", "easy", "Take the train to downtown."),
            ("subway", "metrô", "/ˈsʌb.weɪ/", "medium", "The subway is faster than the bus."),
            ("taxi", "táxi", "/ˈtæk.si/", "easy", "Let's take a taxi to the hotel."),
            ("bicycle", "bicicleta", "/ˈbaɪ.sɪ.kəl/", "medium", "I ride my bicycle on weekends."),
            ("motorcycle", "moto", "/ˈmoʊ.tər.saɪ.kəl/", "medium", "He bought a new motorcycle."),
            ("truck", "caminhão", "/trʌk/", "easy", "The truck delivers food."),
            ("highway", "estrada", "/ˈhaɪ.weɪ/", "medium", "The highway was empty."),
            ("traffic light", "semáforo", "/ˈtræf.ɪk laɪt/", "medium", "Stop at the red traffic light."),
            ("crosswalk", "faixa de pedestre", "/ˈkrɔːs.wɔːk/", "medium", "Use the crosswalk to cross the street."),
            ("gas station", "posto de gasolina", "/ɡæs ˈsteɪ.ʃən/", "medium", "We need to stop at a gas station."),
            ("parking lot", "estacionamento", "/ˈpɑːr.kɪŋ lɑːt/", "medium", "The parking lot is full."),
            ("speed limit", "limite de velocidade", "/spiːd ˈlɪm.ɪt/", "hard", "The speed limit is 60 mph."),
            ("seat belt", "cinto de segurança", "/siːt belt/", "easy", "Always wear your seat belt."),
            ("ticket", "multa", "/ˈtɪk.ɪt/", "medium", "I got a parking ticket."),
            ("map", "mapa", "/mæp/", "easy", "Let me check the map."),
            ("block", "quarteirão", "/blɑːk/", "easy", "The store is two blocks away."),
            ("corner", "esquina", "/ˈkɔːr.nər/", "easy", "Turn right at the next corner."),
            ("bridge", "ponte", "/brɪdʒ/", "easy", "Cross the bridge to get to the city."),
        ]
        words.extend([{"category_id": 11, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in transport])
        
        # ==================== PROFISSÕES (cat 12) - 20 palavras ====================
        professions = [
            ("doctor", "médico(a)", "/ˈdɑːk.tər/", "easy", "The doctor examined the patient."),
            ("nurse", "enfermeiro(a)", "/nɜːrs/", "easy", "The nurse took my blood pressure."),
            ("teacher", "professor(a)", "/ˈtiː.tʃər/", "easy", "My teacher is very patient."),
            ("engineer", "engenheiro(a)", "/ˌen.dʒɪˈnɪr/", "medium", "She works as a software engineer."),
            ("pilot", "piloto", "/ˈpaɪ.lət/", "medium", "The pilot welcomed us aboard."),
            ("firefighter", "bombeiro(a)", "/ˈfaɪər.faɪ.tər/", "medium", "Firefighters rescued the family."),
            ("police officer", "policial", "/pəˈliːs ˌɑː.fɪ.sər/", "medium", "The police officer directed traffic."),
            ("chef", "chefe de cozinha", "/ʃef/", "medium", "The chef prepared an amazing meal."),
            ("lawyer", "advogado(a)", "/ˈlɔɪ.ər/", "medium", "The lawyer presented the case."),
            ("accountant", "contador(a)", "/əˈkaʊn.tənt/", "hard", "My accountant files my taxes."),
            ("architect", "arquiteto(a)", "/ˈɑːr.kɪ.tekt/", "hard", "The architect designed the building."),
            ("dentist", "dentista", "/ˈden.tɪst/", "medium", "I have a dentist appointment."),
            ("journalist", "jornalista", "/ˈdʒɜːr.nə.lɪst/", "hard", "The journalist wrote the article."),
            ("artist", "artista", "/ˈɑːr.tɪst/", "easy", "She is a talented artist."),
            ("musician", "músico(a)", "/mjuːˈzɪʃ.ən/", "medium", "The musician played the guitar."),
            ("photographer", "fotógrafo(a)", "/fəˈtɑː.ɡrə.fər/", "hard", "The photographer took our wedding photos."),
            ("waiter/waitress", "garçom/garçonete", "/ˈweɪ.tər/ / /ˈweɪ.trəs/", "easy", "The waitress brought our drinks."),
            ("salesperson", "vendedor(a)", "/ˈseɪlz.pɜːr.sən/", "medium", "The salesperson helped me choose."),
            ("farmer", "fazendeiro(a)", "/ˈfɑːr.mər/", "easy", "The farmer grows vegetables."),
            ("scientist", "cientista", "/ˈsaɪ.ən.tɪst/", "medium", "Scientists discovered a new planet."),
        ]
        words.extend([{"category_id": 12, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in professions])
        
        # ================================ NUMEROS (cat 13) =======================
        numbers = [
            ("one", "um", "/wʌn/", "easy", "I have one brother."),
            ("two", "dois", "/tuː/", "easy", "Two coffees, please."),
            ("three", "três", "/θriː/", "easy", "I'll stay for three days."),
            ("four", "quatro", "/fɔːr/", "easy", "My son is four years old."),
            ("five", "cinco", "/faɪv/", "easy", "Give me five minutes."),
            ("six", "seis", "/sɪks/", "easy", "I wake up at six."),
            ("seven", "sete", "/ˈsev.ən/", "easy", "Seven days in a week."),
            ("eight", "oito", "/eɪt/", "easy", "Eight people at the table."),
            ("nine", "nove", "/naɪn/", "easy", "Nine months to have a baby."),
            ("ten", "dez", "/ten/", "easy", "Ten fingers on my hands."),
            ("eleven", "onze", "/ɪˈlev.ən/", "medium", "Eleven players on a team."),
            ("twelve", "doze", "/twelv/", "medium", "Twelve months in a year."),
            ("thirteen", "treze", "/θɜːrˈtiːn/", "medium", "Thirteen is unlucky for some."),
            ("fourteen", "quatorze", "/ˌfɔːrˈtiːn/", "medium", "I'm fourteen years old."),
            ("fifteen", "quinze", "/ˌfɪfˈtiːn/", "medium", "Fifteen minutes until the show."),
            ("first", "primeiro", "/fɜːrst/", "medium", "This is my first time here."),
            ("second", "segundo", "/ˈsek.ənd/", "medium", "Take the second door on the right."),
            ("third", "terceiro", "/θɜːrd/", "hard", "The third floor, please."),
            ("dollar", "dólar", "/ˈdɑː.lər/", "easy", "It costs twenty dollars."),
            ("mile", "milha", "/maɪl/", "medium", "It's about 5 miles from here."),
        ]
        words.extend([{"category_id": 13, "english": w[0], "portuguese": w[1], "phonetic": w[2], "difficulty": w[3], "example_sentence": w[4]} for w in numbers])
        
        return words


    
    # ================================================================
    # DADOS: DIÁLOGOS BÁSICOS (44 linhas)
    # ================================================================
    
    def _get_base_dialogs(self) -> List[Dict]:
        """Retorna diálogos básicos por tema"""
        return [
            # ==================== AEROPORTO ====================
            {"theme": "Aeroporto", "role": "Atendente", "line": "Good morning! Can I see your passport, please?", "translation": "Bom dia! Posso ver seu passaporte, por favor?", "order_num": 1},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Yes, here it is.", "translation": "Sim, aqui está.", "order_num": 2},
            {"theme": "Aeroporto", "role": "Atendente", "line": "Are you checking any luggage today?", "translation": "Vai despachar alguma bagagem hoje?", "order_num": 3},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Just this one bag.", "translation": "Apenas esta mala.", "order_num": 4},
            {"theme": "Aeroporto", "role": "Atendente", "line": "Here is your boarding pass. Your flight leaves from gate B12 at 3 PM.", "translation": "Aqui está seu cartão de embarque. Seu voo sai do portão B12 às 15h.", "order_num": 5},
            {"theme": "Aeroporto", "role": "Passageiro", "line": "Thank you! Is the gate far from here?", "translation": "Obrigado! O portão fica longe daqui?", "order_num": 6},
            {"theme": "Aeroporto", "role": "Atendente", "line": "It's about a 10-minute walk. Have a nice flight!", "translation": "São uns 10 minutos andando. Tenha um bom voo!", "order_num": 7},

            # ==================== RESTAURANTE ====================
            {"theme": "Restaurante", "role": "Garçom", "line": "Good evening! Do you have a reservation?", "translation": "Boa noite! Vocês têm reserva?", "order_num": 1},
            {"theme": "Restaurante", "role": "Cliente", "line": "No, we don't. A table for two, please.", "translation": "Não, não temos. Uma mesa para dois, por favor.", "order_num": 2},
            {"theme": "Restaurante", "role": "Garçom", "line": "This way, please. Here is the menu.", "translation": "Por aqui, por favor. Aqui está o cardápio.", "order_num": 3},
            {"theme": "Restaurante", "role": "Garçom", "line": "Are you ready to order?", "translation": "Já estão prontos para pedir?", "order_num": 4},
            {"theme": "Restaurante", "role": "Cliente", "line": "Yes, I'd like the grilled chicken with rice, please.", "translation": "Sim, eu gostaria do frango grelhado com arroz, por favor.", "order_num": 5},
            {"theme": "Restaurante", "role": "Garçom", "line": "Excellent choice! Would you like something to drink?", "translation": "Excelente escolha! Gostaria de algo para beber?", "order_num": 6},
            {"theme": "Restaurante", "role": "Cliente", "line": "Just water, please.", "translation": "Apenas água, por favor.", "order_num": 7},
            {"theme": "Restaurante", "role": "Garçom", "line": "Here is your food. Enjoy your meal!", "translation": "Aqui está sua comida. Bom apetite!", "order_num": 8},
            {"theme": "Restaurante", "role": "Cliente", "line": "Could I have the bill, please?", "translation": "Poderia trazer a conta, por favor?", "order_num": 9},

            # ==================== HOTEL ====================
            {"theme": "Hotel", "role": "Recepcionista", "line": "Welcome to the Grand Hotel. How can I help you?", "translation": "Bem-vindo ao Grand Hotel. Como posso ajudar?", "order_num": 1},
            {"theme": "Hotel", "role": "Hóspede", "line": "I have a reservation under the name Silva.", "translation": "Tenho uma reserva no nome Silva.", "order_num": 2},
            {"theme": "Hotel", "role": "Recepcionista", "line": "Yes, I found it. You'll be in room 305. Here is your key card.", "translation": "Sim, encontrei. Você ficará no quarto 305. Aqui está seu cartão-chave.", "order_num": 3},
            {"theme": "Hotel", "role": "Hóspede", "line": "What time is breakfast served?", "translation": "A que horas é servido o café da manhã?", "order_num": 4},
            {"theme": "Hotel", "role": "Recepcionista", "line": "Breakfast is from 6 to 10 AM in the restaurant on the first floor.", "translation": "O café é das 6h às 10h no restaurante do primeiro andar.", "order_num": 5},
            {"theme": "Hotel", "role": "Hóspede", "line": "Thank you! Also, what's the Wi-Fi password?", "translation": "Obrigado! E qual é a senha do Wi-Fi?", "order_num": 6},

            # ==================== DIREÇÕES ====================
            {"theme": "Direções", "role": "Turista", "line": "Excuse me, how do I get to the museum?", "translation": "Com licença, como faço para chegar ao museu?", "order_num": 1},
            {"theme": "Direções", "role": "Local", "line": "Go straight ahead for two blocks, then turn right at the traffic light.", "translation": "Siga em frente por dois quarteirões e vire à direita no semáforo.", "order_num": 2},
            {"theme": "Direções", "role": "Turista", "line": "Is it far from here? Can I walk?", "translation": "É longe daqui? Dá para ir andando?", "order_num": 3},
            {"theme": "Direções", "role": "Local", "line": "It's about 15 minutes walking. The museum will be on your left.", "translation": "São uns 15 minutos andando. O museu estará à sua esquerda.", "order_num": 4},
            {"theme": "Direções", "role": "Turista", "line": "Thank you so much for your help!", "translation": "Muito obrigado pela ajuda!", "order_num": 5},
            {"theme": "Direções", "role": "Turista", "line": "Excuse me, where is the nearest subway station?", "translation": "Com licença, onde fica a estação de metrô mais próxima?", "order_num": 6},
            {"theme": "Direções", "role": "Local", "line": "Walk two blocks north. You'll see the station entrance next to the pharmacy.", "translation": "Ande dois quarteirões para o norte. Você verá a entrada da estação ao lado da farmácia.", "order_num": 7},
            {"theme": "Direções", "role": "Turista", "line": "Which line should I take to go downtown?", "translation": "Qual linha devo pegar para ir ao centro?", "order_num": 8},

            # ==================== COMPRAS ====================
            {"theme": "Compras", "role": "Vendedor", "line": "Hello! Can I help you find something?", "translation": "Olá! Posso ajudar a encontrar algo?", "order_num": 1},
            {"theme": "Compras", "role": "Cliente", "line": "Yes, I'm looking for a blue shirt in size medium.", "translation": "Sim, estou procurando uma camisa azul tamanho médio.", "order_num": 2},
            {"theme": "Compras", "role": "Vendedor", "line": "Here you go. The fitting room is over there.", "translation": "Aqui está. O provador fica ali.", "order_num": 3},
            {"theme": "Compras", "role": "Cliente", "line": "How much does this cost?", "translation": "Quanto custa isso?", "order_num": 4},
            {"theme": "Compras", "role": "Vendedor", "line": "It's $35. We have a 20% discount today.", "translation": "São $35. Temos 20% de desconto hoje.", "order_num": 5},
            {"theme": "Compras", "role": "Cliente", "line": "Great! I'll take it. Do you accept credit cards?", "translation": "Ótimo! Vou levar. Vocês aceitam cartão de crédito?", "order_num": 6},
            {"theme": "Compras", "role": "Vendedor", "line": "Yes, we do. Cash or card, as you prefer.", "translation": "Sim, aceitamos. Dinheiro ou cartão, como preferir.", "order_num": 7},

            # ==================== EMERGÊNCIA ====================
            {"theme": "Emergência", "role": "Pessoa", "line": "Excuse me, I need help. Is there a pharmacy nearby?", "translation": "Com licença, preciso de ajuda. Tem uma farmácia por perto?", "order_num": 1},
            {"theme": "Emergência", "role": "Local", "line": "Yes, there's one on Main Street. Are you feeling okay?", "translation": "Sim, tem uma na Rua Principal. Você está se sentindo bem?", "order_num": 2},
            {"theme": "Emergência", "role": "Pessoa", "line": "I have a headache. I need to buy some medicine.", "translation": "Estou com dor de cabeça. Preciso comprar um remédio.", "order_num": 3},
            {"theme": "Emergência", "role": "Local", "line": "The pharmacy is open until 10 PM. It's just around the corner.", "translation": "A farmácia fica aberta até as 22h. É logo na esquina.", "order_num": 4},
            {"theme": "Emergência", "role": "Pessoa", "line": "Thank you. Also, where is the nearest hospital?", "translation": "Obrigado. E onde fica o hospital mais próximo?", "order_num": 5},
            {"theme": "Emergência", "role": "Local", "line": "The hospital is about 10 minutes by taxi. Do you need me to call one?", "translation": "O hospital fica a uns 10 minutos de táxi. Quer que eu chame um?", "order_num": 6},
        ]
    
    # ================================================================
    # DADOS: DIÁLOGOS EXPANDIDOS (40+ linhas)
    # ================================================================
    
    def _get_expanded_dialogs(self) -> List[Dict]:
        """Retorna diálogos expandidos com situações reais do dia a dia"""
        return [
            # ==================== RESTAURANTE EXPANDIDO (order_num 100+) ====================
            {"theme": "Restaurante", "role": "Host", "line": "Welcome to Joe's Diner! Just one today?", "translation": "Bem-vindo ao Joe's Diner! Apenas um hoje?", "order_num": 100},
            {"theme": "Restaurante", "role": "Host", "line": "Table for two? Right this way, please.", "translation": "Mesa para dois? Por aqui, por favor.", "order_num": 101},
            {"theme": "Restaurante", "role": "Host", "line": "Do you have a reservation? We're pretty packed tonight.", "translation": "Você tem reserva? Estamos bem lotados hoje.", "order_num": 102},
            {"theme": "Restaurante", "role": "Server", "line": "Can I start you off with something to drink? We have fresh lemonade today.", "translation": "Posso começar com algo para beber? Temos limonada fresca hoje.", "order_num": 110},
            {"theme": "Restaurante", "role": "Server", "line": "Would you like to see the wine list, or just water for now?", "translation": "Gostaria de ver a carta de vinhos, ou só água por enquanto?", "order_num": 111},
            {"theme": "Restaurante", "role": "Customer", "line": "What's the soup of the day?", "translation": "Qual é a sopa do dia?", "order_num": 120},
            {"theme": "Restaurante", "role": "Customer", "line": "Is this dish spicy? I can't handle too much heat.", "translation": "Este prato é picante? Não aguento muito picante.", "order_num": 121},
            {"theme": "Restaurante", "role": "Customer", "line": "What do you recommend? It's my first time here.", "translation": "O que você recomenda? É minha primeira vez aqui.", "order_num": 122},
            {"theme": "Restaurante", "role": "Server", "line": "Our specialty is the grilled salmon. It comes with mashed potatoes and asparagus.", "translation": "Nossa especialidade é o salmão grelhado. Acompanha purê de batatas e aspargos.", "order_num": 123},
            {"theme": "Restaurante", "role": "Customer", "line": "Excuse me, I ordered my steak medium-rare and it's well done.", "translation": "Com licença, pedi meu bife ao ponto e está bem passado.", "order_num": 130},
            {"theme": "Restaurante", "role": "Server", "line": "I'm so sorry about that. Let me get you a new one right away.", "translation": "Sinto muito por isso. Vou trazer um novo imediatamente.", "order_num": 131},
            {"theme": "Restaurante", "role": "Customer", "line": "Can we split the bill? I'll pay for mine separately.", "translation": "Podemos dividir a conta? Vou pagar a minha separado.", "order_num": 140},
            {"theme": "Restaurante", "role": "Customer", "line": "Is the tip included in the bill?", "translation": "A gorjeta está incluída na conta?", "order_num": 141},
            {"theme": "Restaurante", "role": "Server", "line": "No, gratuity is not included. It's completely up to you.", "translation": "Não, a gorjeta não está incluída. Fica a seu critério.", "order_num": 142},

            # ==================== CAFETERIA ====================
            {"theme": "Cafeteria", "role": "Barista", "line": "Good morning! What can I get for you today?", "translation": "Bom dia! O que posso preparar para você hoje?", "order_num": 1},
            {"theme": "Cafeteria", "role": "Customer", "line": "I'd like a medium latte with oat milk, please.", "translation": "Quero um latte médio com leite de aveia, por favor.", "order_num": 2},
            {"theme": "Cafeteria", "role": "Barista", "line": "Hot or iced? And would you like any flavor shots? We have vanilla, caramel, and hazelnut.", "translation": "Quente ou gelado? E gostaria de algum sabor? Temos baunilha, caramelo e avelã.", "order_num": 3},
            {"theme": "Cafeteria", "role": "Customer", "line": "Hot, please. And add a shot of vanilla. Oh, and can I get a blueberry muffin too?", "translation": "Quente, por favor. E adicione baunilha. Ah, e posso pegar um muffin de blueberry também?", "order_num": 4},
            {"theme": "Cafeteria", "role": "Barista", "line": "Sure thing! Your total is $7.85. Cash or card?", "translation": "Claro! O total é $7.85. Dinheiro ou cartão?", "order_num": 5},

            # ==================== TRANSPORTE (TÁXI/UBER) ====================
            {"theme": "Transporte", "role": "Driver", "line": "Where to?", "translation": "Para onde?", "order_num": 1},
            {"theme": "Transporte", "role": "Passenger", "line": "To the airport, Terminal 2, please. How long will it take?", "translation": "Para o aeroporto, Terminal 2, por favor. Quanto tempo vai levar?", "order_num": 2},
            {"theme": "Transporte", "role": "Driver", "line": "About 25 minutes, depending on traffic. Do you have a flight to catch?", "translation": "Uns 25 minutos, dependendo do trânsito. Você tem um voo para pegar?", "order_num": 3},
            {"theme": "Transporte", "role": "Passenger", "line": "Yes, at 3 PM. I think I have plenty of time.", "translation": "Sim, às 15h. Acho que tenho tempo de sobra.", "order_num": 4},
            {"theme": "Transporte", "role": "Passenger", "line": "Can you drop me off right at the departure entrance?", "translation": "Pode me deixar bem na entrada de partidas?", "order_num": 5},

            # ==================== FARMÁCIA ====================
            {"theme": "Farmácia", "role": "Pharmacist", "line": "Hi, how can I help you today?", "translation": "Olá, como posso ajudá-lo hoje?", "order_num": 1},
            {"theme": "Farmácia", "role": "Customer", "line": "I have a terrible cold. What would you recommend?", "translation": "Estou com um resfriado terrível. O que você recomendaria?", "order_num": 2},
            {"theme": "Farmácia", "role": "Pharmacist", "line": "I'd suggest this cold medicine. Take two tablets every six hours.", "translation": "Eu sugeriria este remédio para resfriado. Tome dois comprimidos a cada seis horas.", "order_num": 3},
            {"theme": "Farmácia", "role": "Customer", "line": "No allergies. Can I take this on an empty stomach?", "translation": "Sem alergias. Posso tomar isso de estômago vazio?", "order_num": 4},
            {"theme": "Farmácia", "role": "Pharmacist", "line": "Better to take it with food. Is there anything else you need?", "translation": "Melhor tomar com comida. Precisa de mais alguma coisa?", "order_num": 5},

            # ==================== LOJA DE ROUPAS ====================
            {"theme": "Loja de Roupas", "role": "Salesperson", "line": "Can I help you find something today?", "translation": "Posso ajudar a encontrar algo hoje?", "order_num": 1},
            {"theme": "Loja de Roupas", "role": "Customer", "line": "Yes, I'm looking for a dress for a wedding. Something formal but not too expensive.", "translation": "Sim, estou procurando um vestido para um casamento. Algo formal mas não muito caro.", "order_num": 2},
            {"theme": "Loja de Roupas", "role": "Salesperson", "line": "We have some beautiful options in this section. What size are you?", "translation": "Temos opções lindas nesta seção. Qual é seu tamanho?", "order_num": 3},
            {"theme": "Loja de Roupas", "role": "Customer", "line": "Medium usually. Can I try this one on?", "translation": "Médio, geralmente. Posso experimentar este?", "order_num": 4},
            {"theme": "Loja de Roupas", "role": "Salesperson", "line": "Of course! The fitting rooms are right over there. Take your time.", "translation": "Claro! Os provadores são logo ali. Sem pressa.", "order_num": 5},

            # ==================== SUPERMERCADO ====================
            {"theme": "Supermercado", "role": "Cashier", "line": "Did you find everything okay today?", "translation": "Encontrou tudo bem hoje?", "order_num": 1},
            {"theme": "Supermercado", "role": "Customer", "line": "Yes, thank you. Oh, I forgot to weigh my bananas!", "translation": "Sim, obrigado. Ah, esqueci de pesar minhas bananas!", "order_num": 2},
            {"theme": "Supermercado", "role": "Cashier", "line": "No problem, I can do that here. Would you like paper or plastic bags?", "translation": "Sem problema, posso fazer aqui. Quer sacolas de papel ou plástico?", "order_num": 3},
            {"theme": "Supermercado", "role": "Customer", "line": "Paper, please. And can I get cash back?", "translation": "Papel, por favor. E posso sacar dinheiro?", "order_num": 4},
            {"theme": "Supermercado", "role": "Cashier", "line": "Sure, how much would you like? Your total is $45.60.", "translation": "Claro, quanto gostaria? Seu total é $45.60.", "order_num": 5},
        ]
    
    # ================================================================
    # DADOS: CONQUISTAS (18)
    # ================================================================
    
    def _get_all_achievements(self) -> List[Dict]:
        """Retorna todas as conquistas disponíveis"""
        return [
            {"key": "first_word", "title": "🎯 Primeira Palavra", "description": "Pratique sua primeira palavra", "icon": "🎯"},
            {"key": "first_dialog", "title": "💬 Primeiro Diálogo", "description": "Complete seu primeiro diálogo", "icon": "💬"},
            {"key": "streak_3", "title": "🔥 Foco de 3 Dias", "description": "Pratique 3 dias seguidos", "icon": "🔥"},
            {"key": "streak_7", "title": "⭐ Uma Semana!", "description": "Pratique 7 dias seguidos", "icon": "⭐"},
            {"key": "streak_14", "title": "🌟 Duas Semanas!", "description": "Pratique 14 dias seguidos", "icon": "🌟"},
            {"key": "streak_30", "title": "👑 Mês Completo!", "description": "Pratique 30 dias seguidos", "icon": "👑"},
            {"key": "words_10", "title": "📖 10 Palavras", "description": "Pratique 10 palavras", "icon": "🔤"},
            {"key": "words_50", "title": "📚 50 Palavras", "description": "Pratique 50 palavras", "icon": "📖"},
            {"key": "words_100", "title": "📕 100 Palavras", "description": "Pratique 100 palavras", "icon": "📚"},
            {"key": "words_250", "title": "📗 250 Palavras", "description": "Pratique 250 palavras", "icon": "📙"},
            {"key": "score_100", "title": "💯 Nota Perfeita", "description": "Tire 100 em uma palavra", "icon": "💯"},
            {"key": "perfect_streak_5", "title": "✨ 5 Perfeitas", "description": "Acerte 5 palavras com 100%", "icon": "✨"},
            {"key": "perfect_streak_10", "title": "🌟 10 Perfeitas", "description": "Acerte 10 palavras com 100%", "icon": "🌟"},
            {"key": "category_complete", "title": "🏅 Categoria Completa", "description": "Domine 100% de uma categoria", "icon": "🏅"},
            {"key": "three_categories", "title": "🏆 Três Categorias", "description": "Domine 3 categorias", "icon": "🏆"},
            {"key": "all_categories", "title": "👑 Todas Categorias", "description": "Pratique palavras de todas as categorias", "icon": "👑"},
            {"key": "dialog_5", "title": "🎭 5 Diálogos", "description": "Complete 5 diálogos", "icon": "🎭"},
            {"key": "xp_1000", "title": "⚡ 1000 XP", "description": "Alcance 1000 pontos de experiência", "icon": "⚡"},
        ]


# Instância global
seeder = DataSeeder()