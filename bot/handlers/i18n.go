package handlers

import (
	"fmt"
	"strings"

	"github.com/bwmarrin/discordgo"
)

// Short texts sent with the cards, in the language of the member who ran the command (Discord locale,
// same languages as the website). Unknown locales fall back to English.
var messages = map[string]map[string]string{
	"profile_link": {
		"en": "[View full profile on hourglassbot.net](%s)",
		"fr": "[Voir le profil complet sur hourglassbot.net](%s)",
		"es": "[Ver el perfil completo en hourglassbot.net](%s)",
		"pt": "[Ver o perfil completo em hourglassbot.net](%s)",
		"it": "[Vedi il profilo completo su hourglassbot.net](%s)",
		"de": "[Vollständiges Profil auf hourglassbot.net](%s)",
		"pl": "[Zobacz pełny profil na hourglassbot.net](%s)",
		"tr": "[Profilin tamamı hourglassbot.net'te](%s)",
		"ru": "[Полный профиль на hourglassbot.net](%s)",
		"hi": "[hourglassbot.net पर पूरी प्रोफ़ाइल देखें](%s)",
		"ja": "[hourglassbot.net でプロフィールをすべて見る](%s)",
		"ko": "[hourglassbot.net에서 전체 프로필 보기](%s)",
	},
	"versus_link": {
		"en": "[Full comparison on hourglassbot.net](%s)",
		"fr": "[Comparaison complète sur hourglassbot.net](%s)",
		"es": "[Comparación completa en hourglassbot.net](%s)",
		"pt": "[Comparação completa em hourglassbot.net](%s)",
		"it": "[Confronto completo su hourglassbot.net](%s)",
		"de": "[Vollständiger Vergleich auf hourglassbot.net](%s)",
		"pl": "[Pełne porównanie na hourglassbot.net](%s)",
		"tr": "[Karşılaştırmanın tamamı hourglassbot.net'te](%s)",
		"ru": "[Полное сравнение на hourglassbot.net](%s)",
		"hi": "[hourglassbot.net पर पूरी तुलना](%s)",
		"ja": "[hourglassbot.net で比較をすべて見る](%s)",
		"ko": "[hourglassbot.net에서 전체 비교 보기](%s)",
	},
	"server_link": {
		"en": "[Server dashboard on hourglassbot.net](%s)",
		"fr": "[Tableau de bord du serveur sur hourglassbot.net](%s)",
		"es": "[Panel del servidor en hourglassbot.net](%s)",
		"pt": "[Painel do servidor em hourglassbot.net](%s)",
		"it": "[Dashboard del server su hourglassbot.net](%s)",
		"de": "[Server-Dashboard auf hourglassbot.net](%s)",
		"pl": "[Panel serwera na hourglassbot.net](%s)",
		"tr": "[Sunucu paneli hourglassbot.net'te](%s)",
		"ru": "[Панель сервера на hourglassbot.net](%s)",
		"hi": "[hourglassbot.net पर सर्वर डैशबोर्ड](%s)",
		"ja": "[hourglassbot.net のサーバーダッシュボード](%s)",
		"ko": "[hourglassbot.net 서버 대시보드](%s)",
	},
	"top_link": {
		"en": "[Full leaderboard on hourglassbot.net](%s)",
		"fr": "[Classement complet sur hourglassbot.net](%s)",
		"es": "[Clasificación completa en hourglassbot.net](%s)",
		"pt": "[Ranking completo em hourglassbot.net](%s)",
		"it": "[Classifica completa su hourglassbot.net](%s)",
		"de": "[Vollständige Rangliste auf hourglassbot.net](%s)",
		"pl": "[Pełny ranking na hourglassbot.net](%s)",
		"tr": "[Sıralamanın tamamı hourglassbot.net'te](%s)",
		"ru": "[Полный рейтинг на hourglassbot.net](%s)",
		"hi": "[hourglassbot.net पर पूरी लीडरबोर्ड](%s)",
		"ja": "[hourglassbot.net でランキングをすべて見る](%s)",
		"ko": "[hourglassbot.net에서 전체 순위 보기](%s)",
	},
	"no_member": {
		"en": "Hourglass has no activity recorded for **%s** yet.",
		"fr": "Hourglass n’a encore aucune activité enregistrée pour **%s**.",
		"es": "Hourglass aún no tiene actividad registrada para **%s**.",
		"pt": "O Hourglass ainda não registrou atividade de **%s**.",
		"it": "Hourglass non ha ancora registrato attività per **%s**.",
		"de": "Hourglass hat für **%s** noch keine Aktivität erfasst.",
		"pl": "Hourglass nie zarejestrował jeszcze aktywności **%s**.",
		"tr": "Hourglass henüz **%s** için etkinlik kaydetmedi.",
		"ru": "Hourglass пока не записал активность **%s**.",
		"hi": "Hourglass ने **%s** के लिए अभी तक कोई गतिविधि दर्ज नहीं की है।",
		"ja": "Hourglass は **%s** のアクティビティをまだ記録していません。",
		"ko": "Hourglass가 아직 **%s**의 활동을 기록하지 않았어요.",
	},
	"no_members": {
		"en": "Hourglass has no activity recorded for one of these members yet.",
		"fr": "Hourglass n’a encore aucune activité enregistrée pour l’un de ces membres.",
		"es": "Hourglass aún no tiene actividad registrada para uno de estos miembros.",
		"pt": "O Hourglass ainda não registrou atividade de um desses membros.",
		"it": "Hourglass non ha ancora registrato attività per uno di questi membri.",
		"de": "Hourglass hat für eines dieser Mitglieder noch keine Aktivität erfasst.",
		"pl": "Hourglass nie zarejestrował jeszcze aktywności jednego z tych członków.",
		"tr": "Hourglass bu üyelerden biri için henüz etkinlik kaydetmedi.",
		"ru": "Hourglass пока не записал активность одного из этих участников.",
		"hi": "Hourglass ने इनमें से एक सदस्य के लिए अभी तक कोई गतिविधि दर्ज नहीं की है।",
		"ja": "Hourglass はこのメンバーの一人のアクティビティをまだ記録していません。",
		"ko": "Hourglass가 아직 이 멤버 중 한 명의 활동을 기록하지 않았어요.",
	},
	"no_server": {
		"en": "Hourglass has no activity recorded for this server yet.",
		"fr": "Hourglass n’a encore aucune activité enregistrée pour ce serveur.",
		"es": "Hourglass aún no tiene actividad registrada para este servidor.",
		"pt": "O Hourglass ainda não registrou atividade neste servidor.",
		"it": "Hourglass non ha ancora registrato attività per questo server.",
		"de": "Hourglass hat für diesen Server noch keine Aktivität erfasst.",
		"pl": "Hourglass nie zarejestrował jeszcze aktywności na tym serwerze.",
		"tr": "Hourglass bu sunucu için henüz etkinlik kaydetmedi.",
		"ru": "Hourglass пока не записал активность на этом сервере.",
		"hi": "Hourglass ने इस सर्वर के लिए अभी तक कोई गतिविधि दर्ज नहीं की है।",
		"ja": "Hourglass はこのサーバーのアクティビティをまだ記録していません。",
		"ko": "Hourglass가 아직 이 서버의 활동을 기록하지 않았어요.",
	},
	"two_members": {
		"en": "Please designate two valid members for the duel.",
		"fr": "Choisis deux membres valides pour le duel.",
		"es": "Elige dos miembros válidos para el duelo.",
		"pt": "Escolha dois membros válidos para o duelo.",
		"it": "Scegli due membri validi per la sfida.",
		"de": "Wähle zwei gültige Mitglieder für das Duell.",
		"pl": "Wybierz dwóch prawidłowych członków do pojedynku.",
		"tr": "Düello için iki geçerli üye seç.",
		"ru": "Выбери двух участников для дуэли.",
		"hi": "मुकाबले के लिए दो मान्य सदस्य चुनो।",
		"ja": "対決するメンバーを2人選んでください。",
		"ko": "대결할 멤버 두 명을 선택해 주세요.",
	},
	"server_only": {
		"en": "This command can only be used inside a server. Try `/allstats` or `/alltop` here.",
		"fr": "Cette commande ne marche que sur un serveur. Essaie `/allstats` ou `/alltop` ici.",
		"es": "Este comando solo funciona en un servidor. Prueba `/allstats` o `/alltop` aquí.",
		"pt": "Este comando só funciona em um servidor. Tente `/allstats` ou `/alltop` aqui.",
		"it": "Questo comando funziona solo in un server. Prova `/allstats` o `/alltop` qui.",
		"de": "Dieser Befehl funktioniert nur auf einem Server. Versuche hier `/allstats` oder `/alltop`.",
		"pl": "Ta komenda działa tylko na serwerze. Spróbuj tutaj `/allstats` lub `/alltop`.",
		"tr": "Bu komut yalnızca bir sunucuda çalışır. Burada `/allstats` veya `/alltop` dene.",
		"ru": "Эта команда работает только на сервере. Попробуй здесь `/allstats` или `/alltop`.",
		"hi": "यह कमांड सिर्फ़ सर्वर में चलती है। यहाँ `/allstats` या `/alltop` आज़माओ।",
		"ja": "このコマンドはサーバー内でのみ使えます。ここでは `/allstats` か `/alltop` を試してください。",
		"ko": "이 명령어는 서버에서만 쓸 수 있어요. 여기서는 `/allstats`나 `/alltop`을 써 보세요.",
	},
	"vote_intro": {
		"en": "**[Vote for Hourglass on top.gg](%s)**: it helps other servers find the bot. You can vote every 12 hours, and each vote counts toward the **Supporter** badge.",
		"fr": "**[Vote pour Hourglass sur top.gg](%s)** : ça aide d'autres serveurs à découvrir le bot. Tu peux voter toutes les 12 heures, et chaque vote compte pour le badge **Soutien**.",
		"es": "**[Vota por Hourglass en top.gg](%s)**: ayuda a otros servidores a descubrir el bot. Puedes votar cada 12 horas y cada voto cuenta para la insignia **Apoyo**.",
		"pt": "**[Vote no Hourglass no top.gg](%s)**: isso ajuda outros servidores a descobrir o bot. Você pode votar a cada 12 horas, e cada voto conta para o emblema **Apoio**.",
		"it": "**[Vota Hourglass su top.gg](%s)**: aiuta altri server a scoprire il bot. Puoi votare ogni 12 ore e ogni voto conta per il badge **Sostegno**.",
		"de": "**[Stimme auf top.gg für Hourglass](%s)**: So finden andere Server den Bot. Du kannst alle 12 Stunden abstimmen, und jede Stimme zählt für das Abzeichen **Unterstützung**.",
		"pl": "**[Zagłosuj na Hourglass na top.gg](%s)**: pomagasz innym serwerom odkryć bota. Możesz głosować co 12 godzin, a każdy głos liczy się do odznaki **Wsparcie**.",
		"tr": "**[top.gg'de Hourglass'a oy ver](%s)**: diğer sunucuların botu keşfetmesine yardım eder. 12 saatte bir oy verebilirsin ve her oy **Destek** rozetine sayılır.",
		"ru": "**[Проголосуйте за Hourglass на top.gg](%s)**: так другие серверы узнают о боте. Голосовать можно раз в 12 часов, и каждый голос идёт в значок **Поддержка**.",
		"hi": "**[top.gg पर Hourglass को वोट करें](%s)**: इससे दूसरे सर्वर बॉट को खोज पाते हैं। आप हर 12 घंटे में वोट कर सकते हैं, और हर वोट **समर्थन** बैज में गिना जाता है।",
		"ja": "**[top.gg で Hourglass に投票](%s)**：ほかのサーバーがボットを見つけやすくなります。12時間ごとに投票でき、1票ごとに **応援** バッジにカウントされます。",
		"ko": "**[top.gg에서 Hourglass에 투표하기](%s)**: 다른 서버가 봇을 찾는 데 도움이 돼요. 12시간마다 투표할 수 있고, 투표마다 **응원** 배지에 반영돼요.",
	},
	"vote_count": {
		"en": "Your votes: **%d**",
		"fr": "Tes votes : **%d**",
		"es": "Tus votos: **%d**",
		"pt": "Seus votos: **%d**",
		"it": "I tuoi voti: **%d**",
		"de": "Deine Stimmen: **%d**",
		"pl": "Twoje głosy: **%d**",
		"tr": "Oyların: **%d**",
		"ru": "Ваши голоса: **%d**",
		"hi": "आपके वोट: **%d**",
		"ja": "あなたの投票数：**%d**",
		"ko": "내 투표 수: **%d**",
	},
	"vote_next": {
		"en": "Thanks for your vote! Next vote %s.",
		"fr": "Merci pour ton vote ! Prochain vote %s.",
		"es": "¡Gracias por tu voto! Próximo voto %s.",
		"pt": "Obrigado pelo seu voto! Próximo voto %s.",
		"it": "Grazie per il tuo voto! Prossimo voto %s.",
		"de": "Danke für deine Stimme! Nächste Stimme %s.",
		"pl": "Dzięki za głos! Następny głos %s.",
		"tr": "Oyun için teşekkürler! Sonraki oy %s.",
		"ru": "Спасибо за голос! Следующий голос %s.",
		"hi": "वोट के लिए धन्यवाद! अगला वोट %s।",
		"ja": "投票ありがとうございます！次の投票は %s。",
		"ko": "투표해 주셔서 고마워요! 다음 투표는 %s.",
	},
	"vote_ready": {
		"en": "You can vote now!",
		"fr": "Tu peux voter maintenant !",
		"es": "¡Ya puedes votar!",
		"pt": "Você já pode votar!",
		"it": "Puoi votare adesso!",
		"de": "Du kannst jetzt abstimmen!",
		"pl": "Możesz już głosować!",
		"tr": "Şimdi oy verebilirsin!",
		"ru": "Можно голосовать прямо сейчас!",
		"hi": "आप अभी वोट कर सकते हैं!",
		"ja": "今すぐ投票できます！",
		"ko": "지금 투표할 수 있어요!",
	},
}

// lang returns the site language code for the Discord locale of the member (fr, en-US, pt-BR, es-419...).
func lang(i *discordgo.InteractionCreate) string {
	code, _, _ := strings.Cut(strings.ToLower(string(i.Locale)), "-")
	if _, ok := messages["no_server"][code]; ok {
		return code
	}
	return "en"
}

// msg returns the text key in the member's language, formatted with args.
func msg(i *discordgo.InteractionCreate, key string, args ...interface{}) string {
	text, ok := messages[key][lang(i)]
	if !ok {
		text = messages[key]["en"]
	}
	if len(args) == 0 {
		return text
	}
	return fmt.Sprintf(text, args...)
}
