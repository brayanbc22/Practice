#!/usr/bin/env python3
"""
Script para descargar videos de YouTube con detección real de calidades
Maneja correctamente los formatos ocultos de YouTube
Requiere: pip install yt-dlp
"""

import os
import sys
import argparse
from pathlib import Path
import re

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp no está instalado.")
    print("Instálalo con: pip install yt-dlp")
    sys.exit(1)


class YouTubeDownloader:
    def __init__(self, download_path="./downloads"):
        self.download_path = Path(download_path)
        self.download_path.mkdir(exist_ok=True)
        
        # Configuración base
        self.base_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'writeinfojson': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['es', 'en'],
            'ignoreerrors': True,
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
    
    def _progress_hook(self, d):
        """Hook para mostrar progreso en una sola línea"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            size = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', 'N/A'))
            filename = os.path.basename(d.get('filename', ''))
            
            # Truncar nombre si es muy largo
            if len(filename) > 40:
                filename = filename[:37] + "..."
            
            # Limpiar línea y mostrar progreso
            print(f"\r📥 {filename} | {percent} | {speed} | {size}", end='', flush=True)
            
        elif d['status'] == 'finished':
            filename = os.path.basename(d.get('filename', ''))
            if len(filename) > 50:
                filename = filename[:47] + "..."
            print(f"\r✅ Completado: {filename}" + " " * 20)

    def test_format_availability(self, url):
        """Prueba qué formatos están realmente disponibles"""
        print("🔍 Detectando calidades reales disponibles...")
        
        # Lista de formatos comunes a probar
        test_formats = [
            ('best', 'Mejor calidad automática'),
            ('bestvideo+bestaudio/best', 'Mejor video + audio'),
            ('worst', 'Peor calidad'),
            ('bestvideo[height<=2160]+bestaudio/best', 'Hasta 4K (2160p)'),
            ('bestvideo[height<=1440]+bestaudio/best', 'Hasta 2K (1440p)'),
            ('bestvideo[height<=1080]+bestaudio/best', 'Hasta 1080p'),
            ('bestvideo[height<=720]+bestaudio/best', 'Hasta 720p'),
            ('bestvideo[height<=480]+bestaudio/best', 'Hasta 480p'),
            ('bestvideo[height<=360]+bestaudio/best', 'Hasta 360p'),
        ]
        
        available_formats = []
        
        try:
            # Obtener info básica
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                
                # Si el video es muy largo, usar muestra más pequeña para las pruebas
                test_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'simulate': True,
                    'forceprint': ['format_id', 'resolution', 'ext', 'filesize_approx'],
                }
                
                for format_selector, description in test_formats:
                    try:
                        test_opts['format'] = format_selector
                        with yt_dlp.YoutubeDL(test_opts) as test_ydl:
                            test_info = test_ydl.extract_info(url, download=False)
                            
                            # Intentar obtener la resolución real que se seleccionaría
                            if 'requested_formats' in test_info:
                                # Formato combinado (video + audio separados)
                                video_format = None
                                audio_format = None
                                
                                for fmt in test_info['requested_formats']:
                                    if fmt.get('vcodec', 'none') != 'none':
                                        video_format = fmt
                                    if fmt.get('acodec', 'none') != 'none':
                                        audio_format = fmt
                                
                                if video_format:
                                    height = video_format.get('height')
                                    width = video_format.get('width')
                                    fps = video_format.get('fps')
                                    vcodec = video_format.get('vcodec', '')
                                    
                                    resolution = f"{width}x{height}" if width and height else f"{height}p" if height else "N/A"
                                    fps_info = f" @{fps}fps" if fps else ""
                                    codec_info = f" ({vcodec.split('.')[0]})" if vcodec else ""
                                    
                                    available_formats.append({
                                        'selector': format_selector,
                                        'description': description,
                                        'resolution': resolution,
                                        'height': height or 0,
                                        'fps': fps,
                                        'codec': vcodec,
                                        'type': 'combined_separate',
                                        'display': f"{resolution}{fps_info}{codec_info}"
                                    })
                            else:
                                # Formato directo
                                height = test_info.get('height')
                                width = test_info.get('width')
                                fps = test_info.get('fps')
                                vcodec = test_info.get('vcodec', '')
                                acodec = test_info.get('acodec', '')
                                
                                if height:
                                    resolution = f"{width}x{height}" if width and height else f"{height}p"
                                    fps_info = f" @{fps}fps" if fps else ""
                                    
                                    format_type = 'combined_direct' if acodec and acodec != 'none' else 'video_only'
                                    codec_info = f" ({vcodec.split('.')[0]})" if vcodec else ""
                                    
                                    available_formats.append({
                                        'selector': format_selector,
                                        'description': description,
                                        'resolution': resolution,
                                        'height': height,
                                        'fps': fps,
                                        'codec': vcodec,
                                        'type': format_type,
                                        'display': f"{resolution}{fps_info}{codec_info}"
                                    })
                    except:
                        continue
                
                return {
                    'info': info,
                    'available_formats': available_formats
                }
                
        except Exception as e:
            print(f"❌ Error al detectar formatos: {str(e)}")
            return None

    def get_manual_formats(self, url):
        """Obtiene formatos usando el método tradicional de yt-dlp"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                video_formats = []
                audio_formats = []
                combined_formats = []
                
                for f in formats:
                    height = f.get('height')
                    vcodec = f.get('vcodec', 'none')
                    acodec = f.get('acodec', 'none')
                    
                    if vcodec != 'none' and acodec != 'none' and height:
                        # Formato combinado real
                        combined_formats.append({
                            'format_id': f['format_id'],
                            'height': height,
                            'ext': f.get('ext', 'unknown'),
                            'fps': f.get('fps'),
                            'filesize': f.get('filesize', 0),
                            'vcodec': vcodec,
                            'acodec': acodec
                        })
                    elif vcodec != 'none' and height:
                        # Solo video
                        video_formats.append({
                            'format_id': f['format_id'],
                            'height': height,
                            'ext': f.get('ext', 'unknown'),
                            'fps': f.get('fps'),
                            'filesize': f.get('filesize', 0),
                            'vcodec': vcodec
                        })
                    elif acodec != 'none':
                        # Solo audio
                        audio_formats.append({
                            'format_id': f['format_id'],
                            'abr': f.get('abr'),
                            'ext': f.get('ext', 'unknown'),
                            'filesize': f.get('filesize', 0),
                            'acodec': acodec
                        })
                
                # Ordenar por calidad
                combined_formats.sort(key=lambda x: x['height'], reverse=True)
                video_formats.sort(key=lambda x: x['height'], reverse=True)
                audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                
                return {
                    'combined': combined_formats,
                    'video': video_formats,
                    'audio': audio_formats
                }
        except:
            return {'combined': [], 'video': [], 'audio': []}

    def format_filesize(self, size):
        """Convierte bytes a formato legible"""
        if not size or size == 0:
            return "~N/A"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"~{size:.1f} {unit}"
            size /= 1024.0
        return f"~{size:.1f} TB"

    def select_quality(self, url):
        """Permite al usuario seleccionar la calidad de descarga"""
        # Obtener información usando ambos métodos
        smart_formats = self.test_format_availability(url)
        manual_formats = self.get_manual_formats(url)
        
        if not smart_formats:
            print("❌ No se pudo obtener información del video")
            return 'bestvideo+bestaudio/best'
        
        info = smart_formats['info']
        print(f"\n📺 Título: {info.get('title', 'N/A')}")
        print(f"⏱️  Duración: {info.get('duration', 'N/A')} segundos")
        print(f"👤 Canal: {info.get('uploader', 'N/A')}")
        print(f"👁️  Vistas: {info.get('view_count', 'N/A'):,}" if info.get('view_count') else "👁️  Vistas: N/A")
        
        print("\n" + "="*80)
        print("CALIDADES DETECTADAS")
        print("="*80)
        
        all_options = []
        option_num = 1
        
        # Mostrar formatos detectados inteligentemente
        print(f"\n🎯 CALIDADES REALES DISPONIBLES (Recomendado)")
        print("-" * 70)
        
        # Remover duplicados y ordenar por calidad
        seen_heights = set()
        unique_formats = []
        
        for fmt in smart_formats['available_formats']:
            height = fmt.get('height', 0)
            if height > 0 and height not in seen_heights:
                seen_heights.add(height)
                unique_formats.append(fmt)
        
        # Ordenar por altura (calidad)
        unique_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        
        for fmt in unique_formats:
            if fmt['height'] > 0:  # Solo mostrar formatos con resolución conocida
                type_icon = "🎬" if 'combined' in fmt['type'] else "🎥"
                print(f"{option_num:2d}. {type_icon} {fmt['display']:25} | {fmt['description']}")
                all_options.append(fmt['selector'])
                option_num += 1
        
        # Mostrar formatos manuales si existen y son diferentes
        if manual_formats['combined']:
            print(f"\n📋 FORMATOS COMBINADOS DIRECTOS (De la API)")
            print("-" * 70)
            for fmt in manual_formats['combined'][:5]:  # Limitar a 5
                size = self.format_filesize(fmt['filesize'])
                fps_info = f" @{fmt['fps']}fps" if fmt['fps'] else ""
                height_label = f"{fmt['height']}p"
                if fmt['height'] >= 2160:
                    height_label += " (4K)"
                elif fmt['height'] >= 1440:
                    height_label += " (2K)"
                elif fmt['height'] >= 1080:
                    height_label += " (Full HD)"
                
                print(f"{option_num:2d}. 🎬 {height_label:15}{fps_info:10} | {fmt['ext'].upper()} | {size}")
                all_options.append(fmt['format_id'])
                option_num += 1
        
        # Mostrar solo video (alta calidad)
        if manual_formats['video']:
            print(f"\n🎥 SOLO VIDEO (Máxima calidad + audio por separado)")
            print("-" * 70)
            for fmt in manual_formats['video'][:5]:
                size = self.format_filesize(fmt['filesize'])
                fps_info = f" @{fmt['fps']}fps" if fmt['fps'] else ""
                height_label = f"{fmt['height']}p"
                if fmt['height'] >= 2160:
                    height_label += " (4K)"
                elif fmt['height'] >= 1440:
                    height_label += " (2K)"
                
                print(f"{option_num:2d}. 🎥 {height_label:15}{fps_info:10} | {fmt['ext'].upper()} | {size}")
                all_options.append(f"{fmt['format_id']}+bestaudio")
                option_num += 1
        
        # Solo audio
        if manual_formats['audio']:
            print(f"\n🎵 SOLO AUDIO")
            print("-" * 70)
            for fmt in manual_formats['audio'][:5]:
                size = self.format_filesize(fmt['filesize'])
                quality = f"{fmt.get('abr', 'N/A')}kbps" if fmt.get('abr') else "N/A"
                print(f"{option_num:2d}. 🎵 {quality:15} | {fmt['ext'].upper()} | {size}")
                all_options.append(fmt['format_id'])
                option_num += 1
        
        # Opciones automáticas adicionales
        print(f"\n⚡ OPCIONES RÁPIDAS")
        print("-" * 70)
        
        quick_options = [
            ('best', '🚀 Mejor calidad automática'),
            ('bestvideo+bestaudio/best', '⭐ Mejor video + audio (recomendado)'),
            ('worst', '📱 Calidad más baja (móvil)'),
        ]
        
        for selector, description in quick_options:
            print(f"{option_num:2d}. {description}")
            all_options.append(selector)
            option_num += 1
        
        print("\n" + "="*80)
        print("💡 NOTA: Las opciones marcadas con 🎯 muestran las calidades REALES")
        print("   disponibles, incluyendo 2K/4K que YouTube a veces oculta en la API")
        
        # Selección del usuario
        while True:
            try:
                choice = input(f"\nSelecciona una opción (1-{len(all_options)}) o 'q' para salir: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(all_options):
                    selected_format = all_options[choice_num]
                    print(f"✅ Seleccionado: {selected_format}")
                    return selected_format
                else:
                    print(f"❌ Opción inválida. Selecciona entre 1 y {len(all_options)}")
                    
            except ValueError:
                print("❌ Por favor, introduce un número válido")
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo...")
                return None

    def download_video(self, url, format_selector=None):
        """Descarga un video de YouTube"""
        try:
            if format_selector is None:
                format_selector = self.select_quality(url)
                
            if format_selector is None:
                print("❌ Descarga cancelada")
                return
            
            opts = self.base_opts.copy()
            opts['format'] = format_selector
            
            print(f"\n🚀 Iniciando descarga...")
            print(f"📁 Carpeta: {self.download_path.absolute()}")
            print(f"🎯 Formato: {format_selector}")
            print("-" * 50)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            print(f"\n🎉 ¡Descarga completada exitosamente!")
            
        except Exception as e:
            print(f"\n❌ Error al descargar: {str(e)}")
            print("💡 Sugerencia: Intenta con 'bestvideo+bestaudio/best' como formato")

    def download_playlist(self, url, format_selector=None):
        """Descarga una playlist completa"""
        try:
            if format_selector is None:
                format_selector = self.select_quality(url)
                
            if format_selector is None:
                print("❌ Descarga cancelada")
                return
            
            opts = self.base_opts.copy()
            opts['format'] = format_selector
            opts['outtmpl'] = str(self.download_path / '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s')
            
            # Obtener info de la playlist
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    print(f"\n📋 Playlist: {info.get('title', 'N/A')}")
                    print(f"📊 Videos: {len(info['entries'])}")
                    
                    confirm = input("\n¿Descargar toda la playlist? (y/n): ")
                    if confirm.lower() not in ['y', 'yes', 's', 'si']:
                        print("❌ Descarga cancelada")
                        return
            
            print(f"\n🚀 Iniciando descarga de playlist...")
            print(f"📁 Carpeta: {self.download_path.absolute()}")
            print(f"🎯 Formato: {format_selector}")
            print("-" * 50)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            print(f"\n🎉 ¡Playlist descargada completamente!")
            
        except Exception as e:
            print(f"\n❌ Error al descargar playlist: {str(e)}")

    def download_audio_only(self, url):
        """Descarga solo el audio en formato MP3"""
        try:
            opts = self.base_opts.copy()
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
            })
            
            print(f"\n🎵 Descargando audio en formato MP3...")
            print(f"📁 Carpeta: {self.download_path.absolute()}")
            print("-" * 50)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            print(f"\n🎉 ¡Audio descargado exitosamente!")
            
        except Exception as e:
            print(f"\n❌ Error al descargar audio: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Descargador de YouTube con detección real de calidades')
    parser.add_argument('url', nargs='?', help='URL del video de YouTube')
    parser.add_argument('-p', '--path', default='./downloads', help='Carpeta de descarga')
    parser.add_argument('-a', '--audio', action='store_true', help='Descargar solo audio (MP3)')
    parser.add_argument('-q', '--quality', help='Formato específico')
    parser.add_argument('--playlist', action='store_true', help='Descargar playlist completa')
    
    args = parser.parse_args()
    
    # Banner
    print("🎬" + "="*78 + "🎬")
    print("                    YOUTUBE DOWNLOADER FINAL")
    print("                 Detección real de todas las calidades")
    print("🎬" + "="*78 + "🎬")
    
    # Si no se proporciona URL como argumento, pedirla
    if not args.url:
        args.url = input("\n📎 Introduce la URL del video de YouTube: ").strip()
    
    if not args.url:
        print("❌ URL requerida")
        sys.exit(1)
    
    # Validar URL
    if 'youtube.com' not in args.url and 'youtu.be' not in args.url:
        print("❌ URL no válida. Debe ser de YouTube.")
        sys.exit(1)
    
    downloader = YouTubeDownloader(args.path)
    
    try:
        if args.audio:
            downloader.download_audio_only(args.url)
        elif args.playlist or 'playlist' in args.url:
            downloader.download_playlist(args.url, args.quality)
        else:
            downloader.download_video(args.url, args.quality)
    except KeyboardInterrupt:
        print("\n\n👋 Descarga interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")


if __name__ == "__main__":
    main()