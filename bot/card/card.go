package card

import (
	"bytes"
	"fmt"
	"image"
	"image/color"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"
	"math"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/fogleman/gg"
	"golang.org/x/image/draw"
	_ "golang.org/x/image/webp"
)

var (
	fontRegular = "fonts/DejaVuSans.ttf"
	fontBold    = "fonts/DejaVuSans-Bold.ttf"
)

func init() {
	candidates := []string{
		"fonts/DejaVuSans.ttf",
		"bot-go/fonts/DejaVuSans.ttf",
		"../bot/fonts/DejaVuSans.ttf",
		"C:/Windows/Fonts/segoeui.ttf",
		"C:/Windows/Fonts/arial.ttf",
		"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			fontRegular = c
			break
		}
	}

	candidatesBold := []string{
		"fonts/DejaVuSans-Bold.ttf",
		"bot-go/fonts/DejaVuSans-Bold.ttf",
		"../bot/fonts/DejaVuSans-Bold.ttf",
		"C:/Windows/Fonts/segoeuib.ttf",
		"C:/Windows/Fonts/arialbd.ttf",
		"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
	}
	for _, c := range candidatesBold {
		if _, err := os.Stat(c); err == nil {
			fontBold = c
			break
		}
	}
}

// FormatDuration convertit des secondes en format lisible (ex: "45.2h", "142h" ou "35m")
func FormatDuration(sec int64) string {
	if sec <= 0 {
		return "0m"
	}
	hours := float64(sec) / 3600.0
	if hours >= 1000 {
		return fmt.Sprintf("%dh", int64(hours))
	} else if hours >= 1.0 {
		return fmt.Sprintf("%.1fh", hours)
	}
	minutes := sec / 60
	if minutes > 0 {
		return fmt.Sprintf("%dm", minutes)
	}
	return fmt.Sprintf("%ds", sec)
}

// FormatNumber formate un nombre avec des espaces (ex: 12 450)
func FormatNumber(n int64) string {
	in := fmt.Sprintf("%d", n)
	out := ""
	for i, c := range in {
		if (len(in)-i)%3 == 0 && i > 0 {
			out += " "
		}
		out += string(c)
	}
	return out
}

// CalculateXPAndLevel calcule l'XP et le niveau selon la formule Hourglass officielle
func CalculateXPAndLevel(totalSeconds, totalMessages int64) (level int, title string, totalXP int64, progressPct float64) {
	if totalSeconds < 0 {
		totalSeconds = 0
	}
	if totalMessages < 0 {
		totalMessages = 0
	}

	voiceMinutes := totalSeconds / 60
	totalXP = voiceMinutes + (totalMessages * 5)

	level = int(math.Sqrt(float64(totalXP)/100.0)) + 1
	currentBaseXP := int64((level - 1) * (level - 1) * 100)
	nextTargetXP := int64(level * level * 100)
	needed := nextTargetXP - currentBaseXP

	if needed > 0 {
		progressPct = math.Min(100.0, math.Max(0.0, float64(totalXP-currentBaseXP)/float64(needed)*100.0))
	} else {
		progressPct = 100.0
	}

	switch {
	case level >= 50:
		title = "Légende Hourglass"
	case level >= 40:
		title = "Grand Maître"
	case level >= 30:
		title = "Vétéran de l'Éther"
	case level >= 20:
		title = "Expert des Ondes"
	case level >= 10:
		title = "Membre Confirmé"
	case level >= 5:
		title = "Initié Actif"
	default:
		title = "Novice Curieux"
	}
	return
}

func fetchImage(url string) (image.Image, error) {
	if url == "" {
		return nil, fmt.Errorf("empty url")
	}
	if strings.Contains(url, "cdn.discordapp.com") {
		if strings.HasSuffix(url, ".webp") {
			url = strings.TrimSuffix(url, ".webp") + ".png"
		} else if strings.Contains(url, ".webp?") {
			url = strings.Replace(url, ".webp?", ".png?", 1)
		}
	}

	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("bad status: %d", resp.StatusCode)
	}

	img, _, err := image.Decode(resp.Body)
	return img, err
}

func drawAvatar(dc *gg.Context, avatarImg image.Image, username string, cx, cy, r float64, borderColor color.Color, ringThickness float64) {
	dc.Push()

	// Anneau de bordure externe avec lueur
	dc.DrawCircle(cx, cy, r+ringThickness)
	dc.SetColor(borderColor)
	dc.Fill()

	// Fond sombre de l'avatar
	dc.DrawCircle(cx, cy, r)
	dc.SetRGB255(30, 41, 59) // #1e293b
	dc.Fill()

	if avatarImg != nil {
		targetSize := int(r * 2)
		resized := image.NewRGBA(image.Rect(0, 0, targetSize, targetSize))
		draw.BiLinear.Scale(resized, resized.Bounds(), avatarImg, avatarImg.Bounds(), draw.Over, nil)

		dc.DrawCircle(cx, cy, r)
		dc.Clip()
		dc.DrawImageAnchored(resized, int(cx), int(cy), 0.5, 0.5)
		dc.ResetClip()
	} else {
		letter := "?"
		runes := []rune(username)
		if len(runes) > 0 {
			letter = strings.ToUpper(string(runes[0]))
		}
		_ = dc.LoadFontFace(fontBold, r*0.95)
		dc.SetRGB255(241, 245, 249)
		dc.DrawStringAnchored(letter, cx, cy, 0.5, 0.45)
	}

	dc.Pop()
}

func truncate(s string, maxRunes int) string {
	r := []rune(s)
	if len(r) > maxRunes {
		return string(r[:maxRunes-1]) + "…"
	}
	return s
}

// =============================================================
// 1. CARTE DE PROFIL & STATS (560 × 220) - DA OFFICIELLE HOURGLASS
// =============================================================

type StatsCardParams struct {
	Username      string
	AvatarURL     string
	ServerName    string
	TotalSeconds  int64
	TotalMessages int64
	Rank          int
	JoinDate      string
	IsGlobal      bool
}

func GenerateStatsCard(p StatsCardParams) ([]byte, error) {
	const (
		W = 560
		H = 220
	)

	dc := gg.NewContext(W, H)

	// 1. Fond sombre avec dégradé subtil (#080e1a -> #111d2e)
	bgGrad := gg.NewLinearGradient(0, 0, float64(W), float64(H))
	bgGrad.AddColorStop(0, color.RGBA{R: 8, G: 14, B: 26, A: 255})   // #080e1a
	bgGrad.AddColorStop(1, color.RGBA{R: 17, G: 29, B: 46, A: 255})  // #111d2e
	dc.SetFillStyle(bgGrad)
	dc.DrawRoundedRectangle(0, 0, float64(W), float64(H), 20)
	dc.Fill()

	// 2. Lueur d'ambiance cyan subtile en haut
	dc.Push()
	dc.DrawEllipse(140, 12, 140, 24)
	dc.SetRGBA255(56, 189, 248, 30) // 0.12 opacity
	dc.Fill()
	dc.Pop()

	// 3. Bordure externe élégante
	dc.SetRGBA255(255, 255, 255, 26) // rgba(255, 255, 255, 0.10)
	dc.SetLineWidth(1.2)
	dc.DrawRoundedRectangle(1, 1, float64(W-2), float64(H-2), 20)
	dc.Stroke()

	// 4. Avatar (cx=64, cy=64, r=36) avec lueur cyan #38bdf8
	avatarImg, _ := fetchImage(p.AvatarURL)
	borderColor := color.RGBA{R: 56, G: 189, B: 248, A: 255}
	drawAvatar(dc, avatarImg, p.Username, 64, 64, 36, borderColor, 3.0)

	// Calcul Gamification XP & Niveau
	level, title, totalXP, progressPct := CalculateXPAndLevel(p.TotalSeconds, p.TotalMessages)

	// 5. Nom d'utilisateur
	_ = dc.LoadFontFace(fontBold, 19)
	dc.SetRGB255(255, 255, 255)
	displayName := truncate(p.Username, 16)

	if !p.IsGlobal {
		// --- FORMAT SERVEUR ---
		dc.DrawString(displayName, 120, 44)

		// Chip Serveur
		cleanServer := truncate(p.ServerName, 18)
		_ = dc.LoadFontFace(fontBold, 10.5)
		sw, _ := dc.MeasureString(cleanServer)
		chipW := math.Max(80, sw+24)
		chipH := 19.0
		chipX := 120.0
		chipY := 52.0

		dc.SetRGBA255(56, 189, 248, 22)
		dc.DrawRoundedRectangle(chipX, chipY, chipW, chipH, 5)
		dc.Fill()
		dc.SetRGBA255(56, 189, 248, 64)
		dc.SetLineWidth(0.8)
		dc.DrawRoundedRectangle(chipX, chipY, chipW, chipH, 5)
		dc.Stroke()

		dc.SetRGB255(56, 189, 248)
		dc.DrawStringAnchored(cleanServer, chipX+chipW/2, chipY+chipH/2, 0.5, 0.42)

		// Badge Niveau
		lvlText := fmt.Sprintf("LVL %d • %s", level, title)
		_ = dc.LoadFontFace(fontBold, 10.5)
		lw, _ := dc.MeasureString(lvlText)
		lvlBadgeW := math.Max(100, lw+20)
		lvlBadgeH := 19.0
		lvlBadgeX := 120.0
		lvlBadgeY := 75.0

		dc.SetRGBA255(88, 101, 242, 56) // #5865F2 avec 22% opacité
		dc.DrawRoundedRectangle(lvlBadgeX, lvlBadgeY, lvlBadgeW, lvlBadgeH, 5)
		dc.Fill()
		dc.SetRGBA255(88, 101, 242, 200)
		dc.SetLineWidth(0.8)
		dc.DrawRoundedRectangle(lvlBadgeX, lvlBadgeY, lvlBadgeW, lvlBadgeH, 5)
		dc.Stroke()

		dc.SetRGB255(129, 140, 248) // #818cf8
		dc.DrawStringAnchored(lvlText, lvlBadgeX+lvlBadgeW/2, lvlBadgeY+lvlBadgeH/2, 0.5, 0.42)

	} else {
		// --- FORMAT GLOBAL ---
		dc.DrawString(displayName, 120, 50)

		// Badge Niveau plus imposant
		lvlText := fmt.Sprintf("LVL %d • %s", level, title)
		_ = dc.LoadFontFace(fontBold, 11)
		lw, _ := dc.MeasureString(lvlText)
		lvlBadgeW := math.Max(110, lw+22)
		lvlBadgeH := 21.0
		lvlBadgeX := 120.0
		lvlBadgeY := 64.0

		dc.SetRGBA255(88, 101, 242, 56)
		dc.DrawRoundedRectangle(lvlBadgeX, lvlBadgeY, lvlBadgeW, lvlBadgeH, 6)
		dc.Fill()
		dc.SetRGBA255(88, 101, 242, 220)
		dc.SetLineWidth(1.0)
		dc.DrawRoundedRectangle(lvlBadgeX, lvlBadgeY, lvlBadgeW, lvlBadgeH, 6)
		dc.Stroke()

		dc.SetRGB255(129, 140, 248)
		dc.DrawStringAnchored(lvlText, lvlBadgeX+lvlBadgeW/2, lvlBadgeY+lvlBadgeH/2, 0.5, 0.42)
	}

	// 6. Badge de Rang empilé (Stacked Pill) en haut à droite
	rankBoxX := 440.0
	rankBoxY := 30.0
	rankBoxW := 96.0
	rankBoxH := 38.0
	dc.SetRGBA255(255, 255, 255, 10)
	dc.DrawRoundedRectangle(rankBoxX, rankBoxY, rankBoxW, rankBoxH, 10)
	dc.Fill()
	dc.SetRGBA255(255, 255, 255, 26)
	dc.SetLineWidth(1.0)
	dc.DrawRoundedRectangle(rankBoxX, rankBoxY, rankBoxW, rankBoxH, 10)
	dc.Stroke()

	rankLabel := "RANG SERVEUR"
	if p.IsGlobal {
		rankLabel = "RANG GLOBAL"
	}
	_ = dc.LoadFontFace(fontBold, 8.5)
	dc.SetRGB255(100, 116, 139) // #64748b
	dc.DrawStringAnchored(rankLabel, rankBoxX+rankBoxW/2, rankBoxY+13, 0.5, 0.5)

	rankVal := "Non classé"
	if p.Rank > 0 {
		rankVal = fmt.Sprintf("#%d", p.Rank)
	}
	_ = dc.LoadFontFace(fontBold, 13)
	dc.SetRGB255(56, 189, 248) // #38bdf8
	dc.DrawStringAnchored(rankVal, rankBoxX+rankBoxW/2, rankBoxY+27, 0.5, 0.5)

	// 7. Ligne de séparation
	dc.SetRGBA255(255, 255, 255, 18)
	dc.SetLineWidth(1.0)
	dc.DrawLine(24, 106, 536, 106)
	dc.Stroke()

	// 8. Tuiles de Statistiques (Cardlets) à y=118
	tileY := 118.0
	tileH := 46.0
	rTile := 8.0

	hoursStr := FormatDuration(p.TotalSeconds)
	msgsStr := FormatNumber(p.TotalMessages)
	xpStr := FormatNumber(totalXP)

	drawTile := func(x, w float64, label, val string, valCol color.Color) {
		dc.SetRGBA255(255, 255, 255, 6)
		dc.DrawRoundedRectangle(x, tileY, w, tileH, rTile)
		dc.Fill()
		dc.SetRGBA255(255, 255, 255, 15)
		dc.SetLineWidth(1.0)
		dc.DrawRoundedRectangle(x, tileY, w, tileH, rTile)
		dc.Stroke()

		// Label
		_ = dc.LoadFontFace(fontBold, 9.5)
		dc.SetRGB255(100, 116, 139)
		dc.DrawString(label, x+10, tileY+16)

		// Valeur
		_ = dc.LoadFontFace(fontBold, 14.5)
		dc.SetColor(valCol)
		dc.DrawString(val, x+10, tileY+36)
	}

	whiteCol := color.RGBA{R: 255, G: 255, B: 255, A: 255}
	cyanCol := color.RGBA{R: 56, G: 189, B: 248, A: 255}

	drawTile(24, 92, "VOCAL", hoursStr, whiteCol)
	drawTile(124, 94, "MESSAGES", msgsStr, whiteCol)

	if !p.IsGlobal {
		drawTile(226, 96, "XP SERVEUR", xpStr, whiteCol)

		joinStr := p.JoinDate
		if joinStr == "" {
			joinStr = "Inconnue"
		}
		drawTile(330, 206, "MEMBRE DEPUIS", joinStr, cyanCol)
	} else {
		drawTile(226, 98, "XP TOTAL", xpStr, whiteCol)

		// Bloc d'information globale sur la droite
		summaryX := 332.0
		summaryW := 204.0
		dc.SetRGBA255(255, 255, 255, 6)
		dc.DrawRoundedRectangle(summaryX, tileY, summaryW, tileH, rTile)
		dc.Fill()
		dc.SetRGBA255(255, 255, 255, 15)
		dc.SetLineWidth(1.0)
		dc.DrawRoundedRectangle(summaryX, tileY, summaryW, tileH, rTile)
		dc.Stroke()

		_ = dc.LoadFontFace(fontBold, 9.5)
		dc.SetRGB255(100, 116, 139)
		dc.DrawString("STATUT GLOBAL", summaryX+10, tileY+16)

		_ = dc.LoadFontFace(fontBold, 13)
		dc.SetRGB255(56, 189, 248)
		dc.DrawString(title, summaryX+10, tileY+36)
	}

	// 9. Barre de Progression XP (x=24, y=178)
	barX := 24.0
	barY := 178.0
	barW := 298.0
	barH := 7.0

	// Fond de la barre
	dc.SetRGBA255(255, 255, 255, 20)
	dc.DrawRoundedRectangle(barX, barY, barW, barH, 3.5)
	dc.Fill()

	// Remplissage avec dégradé Cyan -> Indigo
	fillW := math.Max(6.0, barW*(progressPct/100.0))
	fillGrad := gg.NewLinearGradient(barX, barY, barX+fillW, barY)
	fillGrad.AddColorStop(0, color.RGBA{R: 56, G: 189, B: 248, A: 255})
	fillGrad.AddColorStop(1, color.RGBA{R: 129, G: 140, B: 248, A: 255})
	dc.SetFillStyle(fillGrad)
	dc.DrawRoundedRectangle(barX, barY, fillW, barH, 3.5)
	dc.Fill()

	// Texte sous la barre
	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(100, 116, 139)
	dc.DrawString(fmt.Sprintf("PROCHAIN NIVEAU : %.1f%%", progressPct), barX, barY+20)

	// 10. Watermark officiel en bas à droite
	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(51, 65, 85) // #334155
	dc.DrawStringAnchored("HOURGLASS BOT", float64(W)-24, float64(H)-14, 1.0, 0.5)

	var buf bytes.Buffer
	if err := dc.EncodePNG(&buf); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// =============================================================
// 2. CARTE DE CLASSEMENT TOP 10 (620 × H) - DA OFFICIELLE
// =============================================================

type TopEntry struct {
	Rank     int
	Username string
	Avatar   string
	Value    int64
	ValueStr string
}

func GenerateTopCard(rankingType, period, scope string, entries []TopEntry) ([]byte, error) {
	const (
		W         = 620
		rowHeight = 42.0
		yStart    = 110.0
	)

	n := len(entries)
	if n > 10 {
		n = 10
	}
	if n == 0 {
		n = 1
	}

	H := int(yStart + float64(n)*rowHeight + 35.0)

	dc := gg.NewContext(W, H)

	// Fond sombre avec dégradé (#080e1a -> #111d2e)
	bgGrad := gg.NewLinearGradient(0, 0, float64(W), float64(H))
	bgGrad.AddColorStop(0, color.RGBA{R: 8, G: 14, B: 26, A: 255})
	bgGrad.AddColorStop(1, color.RGBA{R: 17, G: 29, B: 46, A: 255})
	dc.SetFillStyle(bgGrad)
	dc.DrawRoundedRectangle(0, 0, float64(W), float64(H), 20)
	dc.Fill()

	// Lueur d'ambiance en haut
	dc.Push()
	dc.DrawEllipse(float64(W)/2, 16, 180, 24)
	dc.SetRGBA255(56, 189, 248, 25)
	dc.Fill()
	dc.Pop()

	// Bordure externe
	dc.SetRGBA255(255, 255, 255, 26)
	dc.SetLineWidth(1.2)
	dc.DrawRoundedRectangle(1, 1, float64(W-2), float64(H-2), 20)
	dc.Stroke()

	// Header (Titre & Filtres)
	_ = dc.LoadFontFace(fontBold, 18)
	dc.SetRGB255(255, 255, 255)
	mainTitle := "TOP 10 VOCAL"
	if rankingType == "messages" {
		mainTitle = "TOP 10 MESSAGES"
	}
	dc.DrawString(mainTitle, 24, 44)

	// Chip des filtres (Période • Portée)
	filterStr := fmt.Sprintf("%s • %s", period, scope)
	_ = dc.LoadFontFace(fontBold, 10.5)
	fw, _ := dc.MeasureString(filterStr)
	chipW := fw + 20
	chipH := 20.0
	chipX := 24.0
	chipY := 52.0

	dc.SetRGBA255(56, 189, 248, 22)
	dc.DrawRoundedRectangle(chipX, chipY, chipW, chipH, 5)
	dc.Fill()
	dc.SetRGBA255(56, 189, 248, 64)
	dc.SetLineWidth(0.8)
	dc.DrawRoundedRectangle(chipX, chipY, chipW, chipH, 5)
	dc.Stroke()

	dc.SetRGB255(56, 189, 248)
	dc.DrawStringAnchored(filterStr, chipX+chipW/2, chipY+chipH/2, 0.5, 0.42)

	// Watermark Header en haut à droite
	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(100, 116, 139)
	dc.DrawStringAnchored("HOURGLASS LEADERBOARD", float64(W)-24, 44, 1.0, 0.5)

	// Ligne de séparation
	dc.SetRGBA255(255, 255, 255, 18)
	dc.SetLineWidth(1.0)
	dc.DrawLine(20, 84, float64(W)-20, 84)
	dc.Stroke()

	// Rendu des lignes du Leaderboard
	for i, entry := range entries {
		if i >= 10 {
			break
		}

		rank := entry.Rank
		y := yStart + float64(i)*rowHeight

		// Fond alterné pour une meilleure lisibilité
		if i%2 == 0 {
			dc.SetRGBA255(255, 255, 255, 6)
			dc.DrawRoundedRectangle(16, y-18, float64(W)-32, 36, 8)
			dc.Fill()
		}

		// 1. Cercle du Rang (Médailles Podium Or, Argent, Bronze)
		medalBg := color.RGBA{R: 255, G: 255, B: 255, A: 20}
		medalTxt := color.RGBA{R: 148, G: 163, B: 184, A: 255}
		avBorder := color.RGBA{R: 56, G: 189, B: 248, A: 120}

		if rank == 1 {
			medalBg = color.RGBA{R: 245, G: 158, B: 11, A: 255} // Or
			medalTxt = color.RGBA{R: 15, G: 23, B: 42, A: 255}
			avBorder = color.RGBA{R: 245, G: 158, B: 11, A: 255}
		} else if rank == 2 {
			medalBg = color.RGBA{R: 148, G: 163, B: 184, A: 255} // Argent
			medalTxt = color.RGBA{R: 15, G: 23, B: 42, A: 255}
			avBorder = color.RGBA{R: 148, G: 163, B: 184, A: 255}
		} else if rank == 3 {
			medalBg = color.RGBA{R: 217, G: 119, B: 6, A: 255} // Bronze
			medalTxt = color.RGBA{R: 15, G: 23, B: 42, A: 255}
			avBorder = color.RGBA{R: 217, G: 119, B: 6, A: 255}
		} else {
			medalBg = color.RGBA{R: 24, G: 33, B: 47, A: 255}
			medalTxt = color.RGBA{R: 148, G: 163, B: 184, A: 255}
		}

		dc.DrawCircle(36, y, 12)
		dc.SetColor(medalBg)
		dc.Fill()
		if rank > 3 {
			dc.SetRGBA255(255, 255, 255, 25)
			dc.SetLineWidth(1.0)
			dc.DrawCircle(36, y, 12)
			dc.Stroke()
		}

		_ = dc.LoadFontFace(fontBold, 11.5)
		dc.SetColor(medalTxt)
		dc.DrawStringAnchored(fmt.Sprintf("%d", rank), 36, y, 0.5, 0.42)

		// 2. Avatar du membre (32px, r=15)
		avImg, _ := fetchImage(entry.Avatar)
		drawAvatar(dc, avImg, entry.Username, 72, y, 15, avBorder, 1.8)

		// 3. Pseudo
		_ = dc.LoadFontFace(fontBold, 13.5)
		dc.SetRGB255(255, 255, 255)
		cleanUname := truncate(entry.Username, 18)
		dc.DrawString(cleanUname, 98, y+4)

		// 4. Badge Niveau approximatif basé sur la métrique
		var estLevel int
		if rankingType == "messages" {
			estLevel = int(math.Sqrt(float64(entry.Value*5)/100.0)) + 1
		} else {
			estLevel = int(math.Sqrt(float64(entry.Value/60)/100.0)) + 1
		}
		if estLevel < 1 {
			estLevel = 1
		}

		lvlBadgeStr := fmt.Sprintf("Nv. %d", estLevel)
		_ = dc.LoadFontFace(fontBold, 10)
		bw, _ := dc.MeasureString(lvlBadgeStr)
		badgeW := bw + 14
		badgeH := 18.0
		badgeX := 265.0
		badgeY := y - 9.0

		dc.SetRGBA255(88, 101, 242, 45)
		dc.DrawRoundedRectangle(badgeX, badgeY, badgeW, badgeH, 4)
		dc.Fill()
		dc.SetRGBA255(88, 101, 242, 160)
		dc.SetLineWidth(0.8)
		dc.DrawRoundedRectangle(badgeX, badgeY, badgeW, badgeH, 4)
		dc.Stroke()

		dc.SetRGB255(129, 140, 248)
		dc.DrawStringAnchored(lvlBadgeStr, badgeX+badgeW/2, badgeY+badgeH/2, 0.5, 0.42)

		// 5. Valeur alignée à droite
		_ = dc.LoadFontFace(fontBold, 13.5)
		if rankingType == "messages" {
			dc.SetRGB255(192, 132, 252) // #c084fc
			dc.DrawStringAnchored(fmt.Sprintf("%s msgs", entry.ValueStr), float64(W)-32, y+4, 1.0, 0.5)
		} else {
			dc.SetRGB255(56, 189, 248) // #38bdf8
			dc.DrawStringAnchored(entry.ValueStr, float64(W)-32, y+4, 1.0, 0.5)
		}
	}

	// Watermark officiel en bas
	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(51, 65, 85)
	dc.DrawStringAnchored("HOURGLASS BOT", float64(W)-24, float64(H)-14, 1.0, 0.5)

	var buf bytes.Buffer
	if err := dc.EncodePNG(&buf); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// =============================================================
// 3. CARTE DE DUEL VERSUS (600 × 260) - DA OFFICIELLE
// =============================================================

type VersusCardParams struct {
	U1Name    string
	U1Avatar  string
	U1Seconds int64
	U1Msgs    int64

	U2Name    string
	U2Avatar  string
	U2Seconds int64
	U2Msgs    int64

	ServerName string
}

func GenerateVersusCard(p VersusCardParams) ([]byte, error) {
	const (
		W = 600
		H = 260
	)

	dc := gg.NewContext(W, H)

	// 1. Fond sombre avec dégradé (#080e1a -> #111d2e)
	bgGrad := gg.NewLinearGradient(0, 0, float64(W), float64(H))
	bgGrad.AddColorStop(0, color.RGBA{R: 8, G: 14, B: 26, A: 255})
	bgGrad.AddColorStop(1, color.RGBA{R: 17, G: 29, B: 46, A: 255})
	dc.SetFillStyle(bgGrad)
	dc.DrawRoundedRectangle(0, 0, float64(W), float64(H), 20)
	dc.Fill()

	// 2. Lueur d'ambiance duel (Cyan à gauche, Violet à droite)
	dc.Push()
	dc.DrawCircle(90, 40, 100)
	dc.SetRGBA255(56, 189, 248, 20)
	dc.Fill()
	dc.DrawCircle(float64(W)-90, 40, 100)
	dc.SetRGBA255(168, 85, 247, 20)
	dc.Fill()
	dc.Pop()

	// 3. Bordure externe
	dc.SetRGBA255(255, 255, 255, 26)
	dc.SetLineWidth(1.2)
	dc.DrawRoundedRectangle(1, 1, float64(W-2), float64(H-2), 20)
	dc.Stroke()

	// 4. Header (Contexte Duel & Watermark)
	_ = dc.LoadFontFace(fontBold, 10.5)
	duelChip := "DUEL DE STATISTIQUES"
	if p.ServerName != "" {
		duelChip = fmt.Sprintf("DUEL • %s", truncate(p.ServerName, 22))
	}
	dw, _ := dc.MeasureString(duelChip)
	dc.SetRGBA255(56, 189, 248, 22)
	dc.DrawRoundedRectangle(24, 18, dw+20, 20, 5)
	dc.Fill()
	dc.SetRGBA255(56, 189, 248, 64)
	dc.SetLineWidth(0.8)
	dc.DrawRoundedRectangle(24, 18, dw+20, 20, 5)
	dc.Stroke()
	dc.SetRGB255(56, 189, 248)
	dc.DrawStringAnchored(duelChip, 24+(dw+20)/2, 28, 0.5, 0.42)

	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(100, 116, 139)
	dc.DrawStringAnchored("HOURGLASS BOT", float64(W)-24, 28, 1.0, 0.5)

	// 5. Profils des deux Joueurs
	u1Lvl, _, _, _ := CalculateXPAndLevel(p.U1Seconds, p.U1Msgs)
	u2Lvl, _, _, _ := CalculateXPAndLevel(p.U2Seconds, p.U2Msgs)

	// Joueur 1 (Gauche, Cyan)
	u1Img, _ := fetchImage(p.U1Avatar)
	drawAvatar(dc, u1Img, p.U1Name, 58, 76, 26, color.RGBA{R: 56, G: 189, B: 248, A: 255}, 2.5)

	_ = dc.LoadFontFace(fontBold, 16)
	dc.SetRGB255(255, 255, 255)
	dc.DrawString(truncate(p.U1Name, 14), 96, 68)

	_ = dc.LoadFontFace(fontBold, 10)
	u1Badge := fmt.Sprintf("LVL %d", u1Lvl)
	bw1, _ := dc.MeasureString(u1Badge)
	dc.SetRGBA255(88, 101, 242, 45)
	dc.DrawRoundedRectangle(96, 75, bw1+14, 18, 4)
	dc.Fill()
	dc.SetRGBA255(88, 101, 242, 160)
	dc.SetLineWidth(0.8)
	dc.DrawRoundedRectangle(96, 75, bw1+14, 18, 4)
	dc.Stroke()
	dc.SetRGB255(129, 140, 248)
	dc.DrawStringAnchored(u1Badge, 96+(bw1+14)/2, 84, 0.5, 0.42)

	// Joueur 2 (Droite, Violet)
	u2Img, _ := fetchImage(p.U2Avatar)
	drawAvatar(dc, u2Img, p.U2Name, float64(W)-58, 76, 26, color.RGBA{R: 192, G: 132, B: 252, A: 255}, 2.5)

	_ = dc.LoadFontFace(fontBold, 16)
	dc.SetRGB255(255, 255, 255)
	dc.DrawStringAnchored(truncate(p.U2Name, 14), float64(W)-96, 68, 1.0, 0.5)

	_ = dc.LoadFontFace(fontBold, 10)
	u2Badge := fmt.Sprintf("LVL %d", u2Lvl)
	bw2, _ := dc.MeasureString(u2Badge)
	p2BadgeX := float64(W) - 96 - (bw2 + 14)
	dc.SetRGBA255(168, 85, 247, 45)
	dc.DrawRoundedRectangle(p2BadgeX, 75, bw2+14, 18, 4)
	dc.Fill()
	dc.SetRGBA255(168, 85, 247, 160)
	dc.SetLineWidth(0.8)
	dc.DrawRoundedRectangle(p2BadgeX, 75, bw2+14, 18, 4)
	dc.Stroke()
	dc.SetRGB255(192, 132, 252)
	dc.DrawStringAnchored(u2Badge, p2BadgeX+(bw2+14)/2, 84, 0.5, 0.42)

	// Pastille centrale "VS"
	vsX := float64(W) / 2
	vsY := 74.0
	dc.SetRGBA255(255, 255, 255, 12)
	dc.DrawRoundedRectangle(vsX-22, vsY-14, 44, 28, 8)
	dc.Fill()
	dc.SetRGBA255(255, 255, 255, 30)
	dc.SetLineWidth(1.0)
	dc.DrawRoundedRectangle(vsX-22, vsY-14, 44, 28, 8)
	dc.Stroke()

	_ = dc.LoadFontFace(fontBold, 12.5)
	dc.SetRGB255(56, 189, 248)
	dc.DrawStringAnchored("VS", vsX, vsY, 0.5, 0.45)

	// Ligne de séparation
	dc.SetRGBA255(255, 255, 255, 18)
	dc.SetLineWidth(1.0)
	dc.DrawLine(24, 118, float64(W)-24, 118)
	dc.Stroke()

	// 6. Barres comparatives
	barTotalW := float64(W) - 48.0 // 552px

	drawComparisonBar := func(y float64, label string, val1, val2 int64, isDuration bool) {
		str1 := FormatNumber(val1)
		str2 := FormatNumber(val2)
		if isDuration {
			str1 = FormatDuration(val1)
			str2 = FormatDuration(val2)
		}

		// Valeur Joueur 1 (Cyan, Gauche)
		_ = dc.LoadFontFace(fontBold, 13.5)
		dc.SetRGB255(56, 189, 248)
		dc.DrawString(str1, 24, y)

		// Label central
		_ = dc.LoadFontFace(fontBold, 9.5)
		dc.SetRGB255(100, 116, 139)
		dc.DrawStringAnchored(label, float64(W)/2, y, 0.5, 0.5)

		// Valeur Joueur 2 (Violet, Droite)
		_ = dc.LoadFontFace(fontBold, 13.5)
		dc.SetRGB255(192, 132, 252)
		dc.DrawStringAnchored(str2, float64(W)-24, y, 1.0, 0.5)

		// Barre bicolore
		barY := y + 10.0
		barH := 8.0
		dc.SetRGBA255(255, 255, 255, 15)
		dc.DrawRoundedRectangle(24, barY, barTotalW, barH, 4)
		dc.Fill()

		sum := val1 + val2
		ratio := 0.5
		if sum > 0 {
			ratio = float64(val1) / float64(sum)
		}
		if ratio < 0.05 {
			ratio = 0.05
		} else if ratio > 0.95 {
			ratio = 0.95
		}

		p1W := barTotalW * ratio

		// Segment Joueur 1 (Cyan)
		dc.Push()
		dc.DrawRoundedRectangle(24, barY, barTotalW, barH, 4)
		dc.Clip()

		dc.SetRGB255(56, 189, 248)
		dc.DrawRectangle(24, barY, p1W, barH)
		dc.Fill()

		// Segment Joueur 2 (Violet)
		dc.SetRGB255(192, 132, 252)
		dc.DrawRectangle(24+p1W, barY, barTotalW-p1W, barH)
		dc.Fill()

		dc.Pop()
		dc.ResetClip()
	}

	drawComparisonBar(146, "TEMPS VOCAL", p.U1Seconds, p.U2Seconds, true)
	drawComparisonBar(196, "MESSAGES ENVOYÉS", p.U1Msgs, p.U2Msgs, false)

	// Watermark bas
	_ = dc.LoadFontFace(fontBold, 9.5)
	dc.SetRGB255(51, 65, 85)
	dc.DrawStringAnchored("HOURGLASS BOT", float64(W)-24, float64(H)-14, 1.0, 0.5)

	var buf bytes.Buffer
	if err := dc.EncodePNG(&buf); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}
