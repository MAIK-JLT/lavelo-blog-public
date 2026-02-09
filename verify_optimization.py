import requests
import json
import time

# URL de la API (ajusta el puerto si es necesario)
url = "http://localhost:5002/api/chat"

# Payload para crear un post
payload = {
    "message": "Crea un post sobre 'Estrategias de nutrición para un Ironman 70.3' para la categoría racing. Hazlo conciso.",
    "history": []
}

headers = {
    "Content-Type": "application/json"
}

print(f"🚀 Enviando petición a {url}...")
print(f"📧 Mensaje: {payload['message']}")

start_time = time.time()

try:
    response = requests.post(url, json=payload, headers=headers)
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"⏱️ Tiempo total: {duration:.2f} segundos")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Petición exitosa:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verificar si se usó la herramienta
        if data.get('tool_used') == 'create_post':
            print("\n✅ Herramienta create_post fue usada.")
            
            # Verificar si se saltó la segunda llamada (mensaje generado manualmente)
            response_text = data.get('response', '')
            if "✅ **Post creado exitosamente**" in response_text:
                print("\n✅ OPTIMIZACIÓN FUNCIONANDO: Respuesta generada manualmente (sin segunda llamada a Claude).")
            else:
                print("\n⚠️ ALERTA: La respuesta no parece ser la manual. Verificar código.")
            
        else:
            print("\n⚠️ No se usó la herramienta create_post.")
            
    else:
        print(f"\n❌ Error {response.status_code}:")
        print(response.text)

except Exception as e:
    print(f"\n❌ Excepción al conectar: {e}")
