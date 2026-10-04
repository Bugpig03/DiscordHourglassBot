package config

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	DiscordToken string
	DBName       string
	DBUser       string
	DBPassword   string
	DBHost       string
	DBPort       string
}

func LoadConfig() (*Config, error) {
	// Charger le .env s'il existe
	_ = godotenv.Load()

	cfg := &Config{
		DiscordToken: os.Getenv("DISCORD_TOKEN"),
		DBName:       getEnv("POSTGRESQL_DBNAME", "devhourglass"),
		DBUser:       getEnv("POSTGRESQL_USER", "postgres"),
		DBPassword:   getEnv("POSTGRESQL_PASSWORD", "admin"),
		DBHost:       getEnv("POSTGRESQL_HOST", "localhost"),
		DBPort:       getEnv("POSTGRESQL_PORT", "5432"),
	}

	if cfg.DiscordToken == "" {
		return nil, fmt.Errorf("DISCORD_TOKEN n'est pas défini dans les variables d'environnement")
	}

	return cfg, nil
}

func (c *Config) DatabaseURL() string {
	return fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
		c.DBUser, c.DBPassword, c.DBHost, c.DBPort, c.DBName)
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}
