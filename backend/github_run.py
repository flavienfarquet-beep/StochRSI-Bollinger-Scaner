from __future__ import annotations
import asyncio
import os
import sys
import yfinance as yf

# Import direct des fonctions mathématiques natives codées par Emergent
from indicators import bollinger_bands, rsi, stoch_rsi, moving_average
from email_service import send_email

# CONFIGURATION DE VOS ACTIFS (Ajoutez vos Tickers ici !)
LISTE_ACTIFS = ["AAPL", "CW8.PA", "TSLA"] 
EMAIL_ALERTE = "votre-email@exemple.com" # Mettez votre e-mail ici

async def simuler_scan_github():
    print("🚀 Démarrage du scan boursier forcé (Alternative GitHub Actions)...")
    
    for symbol in LISTE_ACTIFS:
        print(f"\n🔍 Analyse de {symbol}...")
        
        # 1. Récupération des cours historiques (Période 1 an, bougies 1 Jour)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            print(f"❌ Impossible de récupérer les données pour {symbol}")
            continue
            
        closes = hist["Close"].tolist()
        last_price = closes[-1]
        
        # 2. Calculs via les fonctions d'Emergent
        rsi_vals = rsi(closes, 14)
        rsi_actuel = rsi_vals[-1] if rsi_vals else None
        
        k_vals, _ = stoch_rsi(closes, 14, 14, 3, 3)
        stoch_k = k_vals[-1] if k_vals else None
        
        upper, _, lower = bollinger_bands(closes, 20, 2.0)
        bb_l = lower[-1]
        
        print(f"   Prix : {last_price:.2f} | RSI : {rsi_actuel:.2f} | Stoch K : {stoch_k:.2f} | Bollinger Inf : {bb_l:.2f}")
        
        # 3. Validation de la Condition de Creux (Bollinger Inférieure + Stoch RSI bas)
        if bb_l is not None and stoch_k is not None:
            # Le prix touche la bande basse (avec 1% de marge) ET le Stochastique est en survente (< 15)
            if last_price <= (bb_l * 1.01) and stoch_k <= 15:
                print(f"🚨 MATCH ! Creux détecté sur {symbol} !")
                
                sujet = f"🚨 Opportunité d'achat Détectée - {symbol}"
                corps = (
                    f"Le scan de 20h00 a détecté un creux majeur sur {symbol}.\n\n"
                    f"Prix Actuel : {last_price:.2f}\n"
                    f"RSI (14) : {rsi_actuel:.2f}\n"
                    f"Stochastique RSI : {stoch_k:.2f}\n"
                    f"Bande Bollinger Basse : {bb_l:.2f}\n"
                )
                
                # Envoi immédiat du mail de notification
                try:
                    send_email(EMAIL_ALERTE, sujet, corps)
                    print(f"✉️ Notification envoyée avec succès à {EMAIL_ALERTE}")
                except Exception as mail_err:
                    print(f"❌ Erreur lors de l'envoi de l'e-mail : {mail_err}")

if __name__ == "__main__":
    try:
        asyncio.run(simuler_scan_github())
        print("\n✅ Script de secours GitHub Actions exécuté avec succès.")
        sys.exit(0)
    except Exception as global_err:
        print(f"\n❌ Erreur critique : {global_err}")
        sys.exit(1)
      
