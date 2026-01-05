from flask import Flask, render_template_string, jsonify
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import csv
import io
import concurrent.futures
import json
import re
import uuid
import random
from collections import Counter

# --- CONFIGURATION ---
app = Flask(__name__)

# Global Headers to prevent 403 Forbidden errors
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- HTML TEMPLATE (Using Raw String r"" to fix SyntaxWarning) ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hunter's Gaze | XL-SOC</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.13.3/cdn.min.js" defer></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #0b1121; color: #e2e8f0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        
        /* Glassmorphism & UI */
        .glass-panel {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        .glass-panel:hover {
            border-color: rgba(255, 255, 255, 0.1);
            background: rgba(30, 41, 59, 0.5);
        }

        /* Interactive Elements */
        .clickable-card { cursor: pointer; }
        .clickable-card:hover { transform: translateY(-2px); box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5); }
        .clickable-card.active-filter { border-color: #60a5fa; background: rgba(59, 130, 246, 0.15); }

        /* Filter Chips */
        .filter-chip {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(15, 23, 42, 0.6);
            color: #94a3b8;
        }
        .filter-chip:hover { background: rgba(255, 255, 255, 0.1); color: white; }
        .filter-chip.active { background: #3b82f6; color: white; border-color: #3b82f6; }

        /* Navigation */
        .nav-item {
            cursor: pointer;
            padding: 10px 18px;
            border-radius: 10px;
            transition: all 0.2s;
            color: #94a3b8;
            font-weight: 600;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .nav-item:hover { background: rgba(255, 255, 255, 0.05); color: #e2e8f0; }
        .nav-item.active {
            background: rgba(59, 130, 246, 0.1);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.2);
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.1);
        }

        /* Table Styles */
        th {
            position: sticky; top: 0;
            background: #0f172a;
            color: #64748b;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 14px;
            z-index: 10;
            border-bottom: 2px solid #1e293b;
        }
        td { padding: 12px 14px; border-bottom: 1px solid #1e293b; font-size: 0.85rem; }
        tr:hover td { background-color: rgba(59, 130, 246, 0.05); }

        /* Modal */
        .modal-overlay {
            background-color: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(4px);
        }
        
        /* Toast Notifications */
        .toast-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 100;
            display: flex; flex-direction: column; gap: 10px;
        }
        .toast {
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(10px);
            border-left: 4px solid #3b82f6;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            font-size: 0.85rem;
            display: flex; align-items: center; gap: 10px;
            animation: slideIn 0.3s ease-out;
            border: 1px solid rgba(255,255,255,0.1);
        }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

        /* Source Badges */
        .badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; border: 1px solid transparent; white-space: nowrap; }
        
        .src-sans { background: rgba(239, 68, 68, 0.1); color: #fca5a5; border-color: rgba(239, 68, 68, 0.2); }
        .src-urlhaus { background: rgba(59, 130, 246, 0.1); color: #93c5fd; border-color: rgba(59, 130, 246, 0.2); }
        .src-threatfox { background: rgba(168, 85, 247, 0.1); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.2); }
        .src-feodo { background: rgba(234, 179, 8, 0.1); color: #fde047; border-color: rgba(234, 179, 8, 0.2); }
        .src-bazaar { background: rgba(16, 185, 129, 0.1); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.2); }
        .src-cisa { background: rgba(249, 115, 22, 0.1); color: #fdba74; border-color: rgba(249, 115, 22, 0.2); }
        .src-osint { background: rgba(99, 102, 241, 0.1); color: #a5b4fc; border-color: rgba(99, 102, 241, 0.2); }
        .src-openphish { background: rgba(244, 63, 94, 0.1); color: #fda4af; border-color: rgba(244, 63, 94, 0.2); }
        .src-tor { background: rgba(148, 163, 184, 0.1); color: #cbd5e1; border-color: rgba(148, 163, 184, 0.2); }
        .src-blocklist { background: rgba(220, 38, 38, 0.1); color: #f87171; border-color: rgba(220, 38, 38, 0.2); }
        .src-botvrij { background: rgba(20, 184, 166, 0.1); color: #5eead4; border-color: rgba(20, 184, 166, 0.2); }
        .src-greensnow { background: rgba(132, 204, 22, 0.1); color: #bef264; border-color: rgba(132, 204, 22, 0.2); }
        .src-vxvault { background: rgba(217, 70, 239, 0.1); color: #f0abfc; border-color: rgba(217, 70, 239, 0.2); }
        .src-phishdb { background: rgba(251, 113, 133, 0.1); color: #fda4af; border-color: rgba(251, 113, 133, 0.2); }
        .src-coin { background: rgba(253, 224, 71, 0.1); color: #fef08a; border-color: rgba(253, 224, 71, 0.2); }
        .src-et { background: rgba(236, 72, 153, 0.1); color: #f9a8d4; border-color: rgba(236, 72, 153, 0.2); }
        .src-sslbl { background: rgba(94, 234, 212, 0.1); color: #99f6e4; border-color: rgba(94, 234, 212, 0.2); }
        .src-binary { background: rgba(165, 180, 252, 0.1); color: #c7d2fe; border-color: rgba(165, 180, 252, 0.2); }
        .src-cins { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border-color: rgba(239, 68, 68, 0.4); }
        .src-spamhaus { background: rgba(100, 116, 139, 0.2); color: #cbd5e1; border-color: rgba(100, 116, 139, 0.4); }
        .src-bambenek { background: rgba(217, 70, 239, 0.2); color: #f0abfc; border-color: rgba(217, 70, 239, 0.4); }
        .src-stopforum { background: rgba(251, 146, 60, 0.2); color: #fdba74; border-color: rgba(251, 146, 60, 0.4); }
        .src-darklist { background: rgba(71, 85, 105, 0.3); color: #94a3b8; border-color: rgba(71, 85, 105, 0.5); }
        .src-proxy { background: rgba(20, 184, 166, 0.2); color: #5eead4; border-color: rgba(20, 184, 166, 0.4); }
        .src-cybercrime { background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border-color: rgba(139, 92, 246, 0.4); }
        .src-urlvir { background: rgba(236, 72, 153, 0.2); color: #f9a8d4; border-color: rgba(236, 72, 153, 0.4); }
        .src-phishstats { background: rgba(244, 63, 94, 0.2); color: #fda4af; border-color: rgba(244, 63, 94, 0.4); }
        .src-mdl { background: rgba(168, 85, 247, 0.2); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.4); }
        .src-dga { background: rgba(250, 204, 21, 0.2); color: #fef08a; border-color: rgba(250, 204, 21, 0.4); }
        .src-apache { background: rgba(225, 29, 72, 0.2); color: #fda4af; border-color: rgba(225, 29, 72, 0.4); }
        .src-cleanmx { background: rgba(20, 184, 166, 0.2); color: #2dd4bf; border-color: rgba(20, 184, 166, 0.4); }
        .src-cybercure { background: rgba(244, 63, 94, 0.2); color: #fb7185; border-color: rgba(244, 63, 94, 0.4); }
        .src-rutgers { background: rgba(168, 85, 247, 0.2); color: #e879f9; border-color: rgba(168, 85, 247, 0.4); }
        .src-nipr { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border-color: rgba(59, 130, 246, 0.4); }
        .src-uce { background: rgba(234, 179, 8, 0.2); color: #fde047; border-color: rgba(234, 179, 8, 0.4); }
        
        .badge-correlated {
            background: rgba(220, 38, 38, 0.9);
            color: white;
            border: 1px solid #f87171;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
            animation: pulse-red 2s infinite;
        }
        
        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        /* Utility */
        .live-dot {
            height: 8px; width: 8px; background-color: #10b981; border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse 2s infinite;
        }
        .paused-dot { height: 8px; width: 8px; background-color: #f59e0b; border-radius: 50%; }
        
        .sim-dot {
            height: 8px; width: 8px; background-color: #3b82f6; border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
            animation: pulse-blue 2s infinite;
        }
        @keyframes pulse-blue {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .custom-scroll::-webkit-scrollbar { width: 6px; }
        .custom-scroll::-webkit-scrollbar-track { background: #0f172a; }
        .custom-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        
        .risk-bar { height: 4px; border-radius: 2px; background: #334155; overflow: hidden; width: 60px; margin-top: 4px; }
        .risk-fill { height: 100%; transition: width 0.3s; }
        .risk-low { background: #22c55e; }
        .risk-med { background: #facc15; }
        .risk-high { background: #f97316; }
        .risk-crit { background: #ef4444; }
        
        /* Select Dropdown Styling */
        select.custom-select {
            background-color: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(51, 65, 85, 0.8);
            color: #cbd5e1;
            font-size: 0.75rem;
            padding: 4px 24px 4px 8px;
            border-radius: 0.375rem;
            outline: none;
            appearance: none;
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%2394a3b8' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
            background-position: right 0.5rem center;
            background-repeat: no-repeat;
            background-size: 1.5em 1.5em;
        }
        select.custom-select:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-6 pb-20 overflow-x-hidden" x-data="dashboard()">

    <!-- Header -->
    <header class="mb-8 flex flex-col xl:flex-row justify-between items-center gap-6 glass-panel p-5 sticky top-2 z-50">
        <div class="flex items-center gap-5">
            <div class="h-12 w-12 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20 ring-1 ring-white/10">
                <i class="fas fa-radar text-xl text-white"></i>
            </div>
            <div>
                <h1 class="text-2xl font-bold text-white tracking-tight">Hunter's Gaze <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">XL-SOC</span></h1>
                <div class="flex items-center gap-2 text-[11px] text-slate-400 font-mono mt-1">
                    <span :class="isSimulation ? 'sim-dot' : (isPaused ? 'paused-dot' : 'live-dot')"></span> 
                    <span x-text="statusText">INITIALIZING...</span>
                    <span class="text-slate-600">|</span>
                    <span x-text="unified.length + ' ACTIVE IOCS'" class="text-blue-400"></span>
                    <span class="text-slate-600">|</span>
                    <span class="text-slate-500">40 SOURCES ACTIVE</span>
                </div>
            </div>
        </div>

        <!-- Central Nav -->
        <div class="flex bg-slate-900/80 p-1.5 rounded-xl border border-white/5 shadow-inner overflow-x-auto max-w-full">
            <div @click="activeTab = 'dashboard'" :class="{'active': activeTab === 'dashboard'}" class="nav-item">
                <i class="fas fa-grid-2"></i> Dashboard
            </div>
            <div @click="activeTab = 'unified'" :class="{'active': activeTab === 'unified'}" class="nav-item">
                <i class="fas fa-stream"></i> Omni-Intel Stream
            </div>
            <div @click="activeTab = 'network'" :class="{'active': activeTab === 'network'}" class="nav-item">
                <i class="fas fa-globe-americas"></i> Map
            </div>
            <div @click="activeTab = 'vulns'" :class="{'active': activeTab === 'vulns'}" class="nav-item">
                <i class="fas fa-shield-halved"></i> Vulns
            </div>
        </div>

        <!-- Controls -->
        <div class="flex gap-3">
            <div class="relative group hidden md:block">
                <i class="fas fa-search absolute left-3 top-3 text-slate-500 text-xs group-focus-within:text-blue-400 transition-colors"></i>
                <input x-model="searchQuery" type="text" placeholder="Search IOCs, Time, Source..." 
                    class="bg-slate-900/80 border border-slate-700 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2.5 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 focus:outline-none w-48 transition-all shadow-inner">
            </div>
            
            <button @click="toggleSimulation()" class="px-3 py-2 rounded-lg transition-colors text-xs border border-white/10" 
                :class="isSimulation ? 'bg-blue-900/50 text-blue-300 border-blue-500/30' : 'bg-slate-800 text-slate-400 hover:text-white'" title="Force Simulation Mode">
                <i class="fas fa-flask"></i>
            </button>
            
            <button @click="togglePause()" class="px-3 py-2 rounded-lg transition-colors text-xs border border-white/10" 
                :class="isPaused ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-slate-800 text-slate-400 hover:text-white'">
                <i class="fas" :class="isPaused ? 'fa-play' : 'fa-pause'"></i>
            </button>

            <button @click="fetchData()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-all text-xs shadow-lg shadow-blue-500/25 font-semibold flex items-center gap-2">
                <i class="fas fa-sync-alt" :class="{'animate-spin': isLoading}"></i>
                <span class="hidden sm:inline">SYNC</span>
            </button>
            
            <div class="relative" x-data="{ open: false }">
                <button @click="open = !open" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 rounded-lg transition-colors text-xs border border-white/10 h-full">
                    <i class="fas fa-download"></i>
                </button>
                <div x-show="open" @click.away="open = false" class="absolute right-0 mt-2 w-32 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 py-1" style="display: none;">
                    <a href="#" @click.prevent="exportJSON()" class="block px-4 py-2 text-xs text-slate-300 hover:bg-slate-700 hover:text-white">Export JSON</a>
                    <a href="#" @click.prevent="exportCSV()" class="block px-4 py-2 text-xs text-slate-300 hover:bg-slate-700 hover:text-white">Export CSV</a>
                    <a href="#" @click.prevent="exportSTIX()" class="block px-4 py-2 text-xs text-purple-400 hover:bg-slate-700 hover:text-white border-t border-slate-700">Export STIX 2.1</a>
                </div>
            </div>
        </div>
    </header>

    <!-- Toast Container -->
    <div class="toast-container">
        <template x-for="toast in toasts" :key="toast.id">
            <div class="toast" x-show="toast.visible" x-transition.duration.300ms>
                <i class="fas fa-check-circle text-green-400"></i>
                <span x-text="toast.message"></span>
            </div>
        </template>
    </div>
    
    <!-- Investigation Modal -->
    <div x-show="investigateItem" class="fixed inset-0 z-[60] flex items-center justify-center p-4 modal-overlay" style="display: none;">
        <div @click.away="investigateItem = null" class="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-lg w-full overflow-hidden">
            <div class="p-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center">
                <h3 class="text-white font-bold flex items-center gap-2">
                    <i class="fas fa-search-plus text-blue-400"></i> Investigate IOC
                </h3>
                <button @click="investigateItem = null" class="text-slate-400 hover:text-white"><i class="fas fa-times"></i></button>
            </div>
            <div class="p-6">
                <div class="bg-slate-950 p-3 rounded border border-slate-800 mb-6 flex justify-between items-center">
                    <code class="text-blue-300 font-mono" x-text="investigateItem"></code>
                    <button @click="copy(investigateItem)" class="text-xs text-slate-500 hover:text-white"><i class="fas fa-copy"></i></button>
                </div>
                
                <div class="grid grid-cols-2 gap-3">
                    <a :href="'https://www.virustotal.com/gui/search/'+investigateItem" target="_blank" class="block p-3 rounded bg-slate-800 hover:bg-blue-900/30 border border-slate-700 hover:border-blue-500 transition-all text-center">
                        <i class="fas fa-shield-virus text-blue-400 mb-1 block text-lg"></i>
                        <span class="text-xs text-slate-300">VirusTotal</span>
                    </a>
                    <a :href="'https://www.abuseipdb.com/check/'+investigateItem" target="_blank" class="block p-3 rounded bg-slate-800 hover:bg-blue-900/30 border border-slate-700 hover:border-blue-500 transition-all text-center">
                        <i class="fas fa-database text-blue-400 mb-1 block text-lg"></i>
                        <span class="text-xs text-slate-300">AbuseIPDB</span>
                    </a>
                    <a :href="'https://www.shodan.io/host/'+investigateItem" target="_blank" class="block p-3 rounded bg-slate-800 hover:bg-blue-900/30 border border-slate-700 hover:border-blue-500 transition-all text-center">
                        <i class="fas fa-globe text-blue-400 mb-1 block text-lg"></i>
                        <span class="text-xs text-slate-300">Shodan</span>
                    </a>
                    <a :href="'https://twitter.com/search?q='+investigateItem" target="_blank" class="block p-3 rounded bg-slate-800 hover:bg-blue-900/30 border border-slate-700 hover:border-blue-500 transition-all text-center">
                        <i class="fab fa-twitter text-blue-400 mb-1 block text-lg"></i>
                        <span class="text-xs text-slate-300">Twitter Intel</span>
                    </a>
                    <a :href="'https://www.google.com/search?q='+investigateItem" target="_blank" class="block p-3 rounded bg-slate-800 hover:bg-blue-900/30 border border-slate-700 hover:border-blue-500 transition-all text-center col-span-2">
                        <i class="fab fa-google text-blue-400 mb-1 block text-lg"></i>
                        <span class="text-xs text-slate-300">Google Dorks</span>
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Content Area -->
    <main>
        
        <!-- DASHBOARD VIEW -->
        <div x-show="activeTab === 'dashboard'" class="animate-fade-in">
            <!-- Metrics (Clickable for Filter) -->
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
                <template x-for="metric in metrics">
                    <div @click="setFilter(metric.filterKey)" 
                         class="glass-panel p-3 flex flex-col justify-between h-20 relative overflow-hidden group clickable-card"
                         :class="{'active-filter': activeFilter === metric.filterKey}">
                        <div class="absolute right-0 top-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
                            <i :class="metric.icon" class="text-3xl"></i>
                        </div>
                        <h3 class="text-slate-500 text-[9px] uppercase font-bold tracking-wider" x-text="metric.label"></h3>
                        <div class="flex items-end gap-2">
                            <span class="text-xl font-bold text-white font-mono" x-text="metric.value">0</span>
                        </div>
                        <div class="h-1 w-full bg-slate-800 rounded-full mt-1 overflow-hidden">
                            <div class="h-full rounded-full transition-all duration-1000" :class="metric.bg" :style="'width: ' + Math.min(100, metric.value * 2) + '%'"></div>
                        </div>
                    </div>
                </template>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                <!-- Threat Radar -->
                <div class="glass-panel h-[400px] flex flex-col">
                    <div class="p-4 border-b border-white/5 bg-white/5">
                        <h2 class="font-bold text-sm text-white flex items-center gap-2">
                            <i class="fas fa-crosshairs text-indigo-400"></i> THREAT RADAR
                        </h2>
                    </div>
                    <div id="chart-radar" class="flex-1 w-full h-full"></div>
                </div>

                <!-- Recent High Severity -->
                <div class="glass-panel lg:col-span-2 h-[400px] flex flex-col">
                    <div class="p-4 border-b border-white/5 flex justify-between items-center bg-white/5">
                        <h2 class="font-bold text-sm text-white flex items-center gap-2">
                            <i class="fas fa-bolt text-amber-400"></i> CRITICAL RISK FEED
                        </h2>
                        <div x-show="isSimulation" class="text-[10px] bg-blue-900/50 text-blue-300 px-2 py-1 rounded border border-blue-500/30">
                            <i class="fas fa-flask mr-1"></i> SIMULATION MODE
                        </div>
                    </div>
                    <div class="overflow-auto flex-1 custom-scroll p-2">
                        <table class="w-full text-left border-collapse">
                            <tbody>
                                <template x-for="item in filteredUnified.slice(0, 10)" :key="item.id">
                                    <tr class="group border-b border-slate-800/50 hover:bg-white/5 transition-colors rounded-lg cursor-pointer" @click="investigate(item.ioc)">
                                        <td class="w-12 text-center"><i :class="item.icon + ' ' + item.colorClass" class="text-lg opacity-80"></i></td>
                                        <td>
                                            <div class="flex flex-col">
                                                <span class="font-mono text-xs text-blue-300 font-bold" x-text="item.ioc"></span>
                                                <div class="flex items-center gap-2">
                                                    <span class="text-[9px] text-slate-500 uppercase" x-text="item.source"></span>
                                                    <span class="text-[9px] text-teal-400" x-text="timeAgo(item.rawTime)"></span>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="hidden md:table-cell">
                                            <div class="flex flex-col gap-1">
                                                <span class="text-[10px] text-slate-400">Risk Score: <span x-text="item.risk + '/10'"></span></span>
                                                <div class="risk-bar">
                                                    <div class="risk-fill" :class="getRiskClass(item.risk)" :style="'width: ' + (item.risk * 10) + '%'"></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td class="text-right">
                                             <button class="text-[10px] bg-slate-800 text-slate-300 px-2 py-1 rounded hover:bg-blue-600 hover:text-white transition-colors group-hover:bg-blue-600/20 group-hover:text-blue-400">
                                                INVESTIGATE <i class="fas fa-arrow-right ml-1"></i>
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- UNIFIED STREAM VIEW -->
        <div x-show="activeTab === 'unified'" class="glass-panel flex flex-col h-[750px] animate-fade-in">
            <div class="p-4 border-b border-white/5 bg-slate-800/40 flex flex-col xl:flex-row justify-between items-center gap-4">
                <div class="flex flex-col sm:flex-row gap-4 items-center w-full xl:w-auto">
                    <h2 class="font-bold text-sm text-white flex items-center gap-2 whitespace-nowrap">
                        <i class="fas fa-satellite-dish text-blue-400"></i> OMNI-INTEL FEED
                    </h2>
                    <select x-model="selectedSource" class="custom-select w-full sm:w-48">
                        <option value="all">All Sources (40)</option>
                        <template x-for="source in allSources" :key="source">
                            <option :value="source" x-text="source"></option>
                        </template>
                    </select>
                </div>
                
                <!-- Filter Chips -->
                <div class="flex flex-wrap justify-center gap-2">
                    <div @click="setFilter('all')" class="filter-chip" :class="{'active': activeFilter === 'all'}">All Categories</div>
                    <div @click="setFilter('correlated')" class="filter-chip border-red-500/50 text-red-300" :class="{'active': activeFilter === 'correlated', 'bg-red-900/20': activeFilter !== 'correlated', 'bg-red-600': activeFilter === 'correlated'}">Correlated</div>
                    <div @click="setFilter('network')" class="filter-chip" :class="{'active': activeFilter === 'network'}">Network</div>
                    <div @click="setFilter('malware')" class="filter-chip" :class="{'active': activeFilter === 'malware'}">Malware</div>
                    <div @click="setFilter('phishing')" class="filter-chip" :class="{'active': activeFilter === 'phishing'}">Phishing</div>
                    <div @click="setFilter('botnet')" class="filter-chip" :class="{'active': activeFilter === 'botnet'}">Botnets</div>
                    <div @click="setFilter('crypto')" class="filter-chip" :class="{'active': activeFilter === 'crypto'}">Crypto</div>
                </div>
            </div>
            
            <div class="overflow-auto flex-1 p-0 custom-scroll">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr>
                            <th class="w-28">Source</th>
                            <th class="w-28">Risk</th>
                            <th>Indicator (IOC)</th>
                            <th class="hidden md:table-cell">Context</th>
                            <th class="text-right">Smart Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/50">
                        <template x-for="item in filteredUnified" :key="item.id">
                            <tr class="transition group hover:bg-slate-800/40">
                                <td>
                                    <span class="badge" :class="item.badgeClass">
                                        <i :class="item.icon"></i> <span x-text="item.source"></span>
                                    </span>
                                </td>
                                <td>
                                    <div class="risk-bar" :title="'Risk Score: ' + item.risk">
                                        <div class="risk-fill" :class="getRiskClass(item.risk)" :style="'width: ' + (item.risk * 10) + '%'"></div>
                                    </div>
                                    <span class="text-[9px] text-slate-500" x-text="timeAgo(item.rawTime)"></span>
                                </td>
                                <td>
                                    <div class="flex flex-col cursor-pointer" @click="copy(item.ioc)" title="Click to Copy">
                                        <div class="flex items-center gap-2">
                                            <span class="font-mono text-xs select-all font-bold group-hover:text-white transition-colors" 
                                                  :class="item.ioc.startsWith('CVE') ? 'text-amber-400' : 'text-blue-400'" 
                                                  x-text="item.ioc"></span>
                                            <span x-show="item.correlated" class="text-[8px] badge-correlated px-1 rounded">MATCHED</span>
                                            <i class="fas fa-copy text-slate-600 text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"></i>
                                        </div>
                                        <span class="text-[9px] text-slate-500 md:hidden" x-text="item.type"></span>
                                    </div>
                                </td>
                                <td class="text-slate-400 text-xs hidden md:table-cell">
                                    <span class="text-[10px] bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-slate-300 mr-2" x-text="item.type"></span>
                                    <span x-text="item.details"></span>
                                </td>
                                <td class="text-right pr-4">
                                    <div class="flex justify-end gap-2">
                                        <a :href="item.link" target="_blank" class="text-slate-500 hover:text-white transition-colors text-[10px] bg-slate-900 p-1.5 px-2 rounded border border-slate-700 hover:border-slate-500">
                                            Source
                                        </a>
                                        <button @click="investigate(item.ioc)" class="text-blue-400 hover:text-white transition-colors text-[10px] bg-blue-900/20 p-1.5 px-2 rounded border border-blue-900/50 hover:bg-blue-600 hover:border-blue-500" title="Deep Dive">
                                            Investigate <i class="fas fa-search-plus ml-1"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </template>
                        <tr x-show="filteredUnified.length === 0">
                            <td colspan="6" class="p-12 text-center text-slate-500">
                                <div class="flex flex-col items-center gap-2">
                                    <i class="fas fa-filter text-3xl opacity-50"></i>
                                    <span>No intelligence matching your filters.</span>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- NETWORK & MAP VIEW -->
        <div x-show="activeTab === 'network'" class="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[750px] animate-fade-in">
            <!-- Global Map -->
            <div class="glass-panel lg:col-span-2 flex flex-col relative overflow-hidden">
                <div class="absolute top-4 left-4 z-10 bg-slate-900/80 p-2 rounded border border-white/10 backdrop-blur">
                    <h2 class="font-bold text-xs text-white"><i class="fas fa-globe-americas text-emerald-400 mr-2"></i>LIVE ATTACK ORIGINS</h2>
                </div>
                <div id="chart-map" class="flex-1 w-full h-full bg-[#0b1121]"></div>
            </div>

            <!-- Network List -->
            <div class="glass-panel flex flex-col">
                <div class="p-4 border-b border-white/5 bg-slate-800/40">
                    <h2 class="font-bold text-sm text-white"><i class="fas fa-network-wired text-red-400 mr-2"></i>ACTIVE INTRUSIONS</h2>
                </div>
                <div class="overflow-auto flex-1 custom-scroll">
                    <table class="w-full text-left">
                        <thead class="bg-slate-900/50"><tr><th class="py-2">IP Addr</th><th class="py-2">Cty</th><th class="py-2 text-right">Reports</th></tr></thead>
                        <tbody>
                            <template x-for="item in data.sans">
                                <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 cursor-pointer" @click="investigate(item.ip)">
                                    <td class="font-mono text-red-300 text-xs p-3" x-text="item.ip"></td>
                                    <td class="text-slate-400 text-xs p-3" x-text="item.country"></td>
                                    <td class="text-right p-3">
                                        <span class="text-[10px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded border border-red-500/20" x-text="item.reports"></span>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- VULNERABILITY WATCH VIEW -->
        <div x-show="activeTab === 'vulns'" class="glass-panel flex flex-col h-[750px] animate-fade-in">
            <div class="p-5 border-b border-white/5 bg-gradient-to-r from-orange-900/20 to-transparent flex justify-between items-center">
                <div>
                    <h2 class="font-bold text-lg text-white flex items-center gap-2">
                        <i class="fas fa-shield-virus text-orange-500"></i> CISA KEV WATCH
                    </h2>
                    <p class="text-xs text-orange-200/50 mt-1">Known Exploited Vulnerabilities Catalog (US-CERT)</p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold text-white" x-text="data.cisa.length">0</div>
                    <div class="text-[10px] text-slate-400 uppercase tracking-wider">Active CVEs</div>
                </div>
            </div>
            <div class="overflow-auto flex-1 p-0 custom-scroll">
                <div class="grid grid-cols-1 gap-1 p-1">
                    <template x-for="item in data.cisa">
                        <div class="bg-slate-800/30 border border-slate-700/50 p-4 rounded-lg hover:bg-slate-800/60 hover:border-orange-500/30 transition-all group">
                            <div class="flex justify-between items-start mb-2">
                                <div class="flex gap-3 items-center">
                                    <span class="font-mono text-sm font-bold text-orange-400 bg-orange-900/20 px-2 py-1 rounded border border-orange-500/20" x-text="item.cveID" @click="copy(item.cveID)"></span>
                                    <span class="text-xs font-semibold text-slate-300" x-text="item.vendorProject + ' ' + item.product"></span>
                                </div>
                                <span class="text-[10px] text-slate-500" x-text="item.dateAdded"></span>
                            </div>
                            <p class="text-sm text-slate-400 mb-3" x-text="item.shortDescription"></p>
                            <div class="flex justify-between items-center">
                                <span class="text-[10px] text-slate-500 bg-slate-900 px-2 py-1 rounded">Required Action: <span class="text-slate-300" x-text="item.requiredAction"></span></span>
                                <a :href="'https://nvd.nist.gov/vuln/detail/' + item.cveID" target="_blank" class="text-orange-400 hover:text-white text-xs flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    NVD Details <i class="fas fa-arrow-right"></i>
                                </a>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

    </main>

    <script>
        document.addEventListener('alpine:init', () => {
            Alpine.data('dashboard', () => ({
                activeTab: 'dashboard',
                activeFilter: 'all',
                selectedSource: 'all',
                isLoading: false,
                isPaused: false,
                isSimulation: false,
                statusText: 'CONNECTING',
                searchQuery: '',
                toasts: [],
                investigateItem: null,
                data: { sans: [], urlhaus: [], threatfox: [], feodo: [], bazaar: [], cisa: [], osint: [], openphish: [], tor: [], blocklist: [], botvrij: [], greensnow: [], vxvault: [], phishdb: [], coinblocker: [], et: [], sslbl: [], binary: [], cins: [], spamhaus: [], bambenek: [], stopforum: [], darklist: [], proxies: [], cybercrime: [], urlvir: [], phishstats: [], mdl: [], dga: [], apache: [], mail: [], ftp: [], imap: [], sip: [], bots: [], cleanmx: [], cybercure: [], rutgers: [], nipr: [], uce: [] },
                unified: [],
                allSources: [],
                metrics: [
                    { label: 'Correlated Threats', value: 0, icon: 'fas fa-link', color: 'text-red-500', bg: 'bg-red-600', filterKey: 'correlated' },
                    { label: 'Network Scan', value: 0, icon: 'fas fa-network-wired', color: 'text-red-400', bg: 'bg-red-500', filterKey: 'network' },
                    { label: 'Botnet IOCs', value: 0, icon: 'fas fa-robot', color: 'text-yellow-400', bg: 'bg-yellow-500', filterKey: 'botnet' },
                    { label: 'Malware URLs', value: 0, icon: 'fas fa-bug', color: 'text-purple-400', bg: 'bg-purple-500', filterKey: 'malware' },
                    { label: 'Phishing', value: 0, icon: 'fas fa-fish', color: 'text-pink-400', bg: 'bg-pink-500', filterKey: 'phishing' },
                    { label: 'Hashes', value: 0, icon: 'fas fa-file-code', color: 'text-green-400', bg: 'bg-green-500', filterKey: 'malware' },
                    { label: 'CVEs', value: 0, icon: 'fas fa-shield-virus', color: 'text-orange-400', bg: 'bg-orange-500', filterKey: 'all' },
                    { label: 'OSINT', value: 0, icon: 'fas fa-eye', color: 'text-indigo-400', bg: 'bg-indigo-500', filterKey: 'all' },
                    { label: 'Anon/Tor', value: 0, icon: 'fas fa-user-secret', color: 'text-slate-400', bg: 'bg-slate-500', filterKey: 'all' },
                    { label: 'Brute Force', value: 0, icon: 'fas fa-fire', color: 'text-red-500', bg: 'bg-red-600', filterKey: 'network' },
                    { label: 'Crypto Mining', value: 0, icon: 'fas fa-coins', color: 'text-yellow-300', bg: 'bg-yellow-400', filterKey: 'crypto' }
                ],

                async fetchData() {
                    if (this.isPaused) return;
                    this.isLoading = true;
                    this.statusText = 'SYNCING INTEL...';
                    
                    try {
                        const res = await fetch('/api/data');
                        const json = await res.json();
                        
                        this.data = json;
                        this.isSimulation = json.simulation || false;
                        
                        this.processUnified();
                        this.updateMetrics();
                        this.renderMap();
                        this.renderRadar();
                        
                        if(this.isSimulation) {
                            this.statusText = 'SIMULATION MODE (LIVE DATA UNAVAILABLE)';
                        } else {
                            this.statusText = 'LIVE | ' + new Date().toLocaleTimeString();
                        }
                        
                    } catch (e) {
                        console.error(e);
                        this.statusText = 'CONNECTION ERROR';
                    } finally {
                        this.isLoading = false;
                    }
                },
                
                toggleSimulation() {
                    this.isSimulation = !this.isSimulation;
                    this.fetchData();
                },
                
                setFilter(key) {
                    this.activeFilter = key;
                    this.activeTab = 'unified';
                    this.selectedSource = 'all'; 
                },
                
                investigate(ioc) {
                    this.investigateItem = ioc;
                },

                processUnified() {
                    let combined = [];
                    let idCounter = 0;
                    const seenSources = new Set();
                    
                    const add = (source, list, mapFn, category, riskScore) => {
                        if (!list) return;
                        seenSources.add(source);
                        list.forEach(item => combined.push({ 
                            id: idCounter++, 
                            source, 
                            category, 
                            risk: riskScore,
                            correlated: item.correlated || false,
                            ...mapFn(item) 
                        }));
                    };

                    add('SANS ISC', this.data.sans, i => ({
                        rawTime: i.updated, ioc: i.ip, type: 'Network Scan', details: `${i.reports} Reports (${i.country})`, 
                        link: `https://isc.sans.edu/ipinfo.html?ip=${i.ip}`, pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-sans', icon: 'fas fa-network-wired', colorClass: 'text-red-400'
                    }), 'network', 5);

                    add('Feodo Tracker', this.data.feodo, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Botnet C2', details: `${i.malware} (Port ${i.port})`,
                        link: `https://feodotracker.abuse.ch/browse/ip/${i.ip}/`, pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-feodo', icon: 'fas fa-robot', colorClass: 'text-yellow-400'
                    }), 'botnet', 9);

                    add('URLhaus', this.data.urlhaus, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Malware URL', details: `${i.threat} (${i.status})`,
                        link: i.link, pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-urlhaus', icon: 'fas fa-link', colorClass: 'text-blue-400'
                    }), 'malware', 8);

                    add('OpenPhish', this.data.openphish, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Phishing URL', details: 'Detected Phishing Site',
                        link: i.url, pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-openphish', icon: 'fas fa-fish', colorClass: 'text-pink-400'
                    }), 'phishing', 7);

                    add('ThreatFox', this.data.threatfox, i => ({
                        rawTime: i.date, ioc: i.ioc, type: i.threat_type, details: `${i.malware} (@${i.reporter})`,
                        link: i.reference, pivotLink: i.ioc.includes('.') ? `https://www.virustotal.com/gui/search/${i.ioc}` : `https://www.abuseipdb.com/check/${i.ioc}`,
                        badgeClass: 'src-threatfox', icon: 'fas fa-brain', colorClass: 'text-purple-400'
                    }), 'botnet', 9);

                    add('MalwareBazaar', this.data.bazaar, i => ({
                        rawTime: i.date, ioc: i.hash, type: i.type, details: `${i.signature}`,
                        link: i.link, pivotLink: `https://www.virustotal.com/gui/file/${i.hash}`,
                        badgeClass: 'src-bazaar', icon: 'fas fa-file-code', colorClass: 'text-green-400'
                    }), 'malware', 8);

                    add('CISA KEV', this.data.cisa.slice(0,10), i => ({
                        rawTime: i.dateAdded, ioc: i.cveID, type: 'Exploited Vuln', details: i.product,
                        link: `https://nvd.nist.gov/vuln/detail/${i.cveID}`, pivotLink: `https://cve.mitre.org/cgi-bin/cvename.cgi?name=${i.cveID}`,
                        badgeClass: 'src-cisa', icon: 'fas fa-shield-virus', colorClass: 'text-orange-400'
                    }), 'all', 10);
                    
                    add('Tor Exit', this.data.tor, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Anonymizer', details: 'Tor Exit Node',
                        link: `https://metrics.torproject.org/rs.html#search/${i.ip}`, pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-tor', icon: 'fas fa-user-secret', colorClass: 'text-slate-400'
                    }), 'all', 3);

                    add('Blocklist.de', this.data.blocklist, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'SSH Brute Force', details: 'Aggressive Scanner',
                        link: `https://lists.blocklist.de/lists/ssh.txt`, pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-key', colorClass: 'text-red-500'
                    }), 'network', 6);
                    
                    add('DigitalSide', this.data.osint, i => ({
                        rawTime: new Date().toISOString().split('T')[0], ioc: i.ioc, type: 'OSINT Domain', details: 'Malicious Domain List',
                        link: '#', pivotLink: `https://urlscan.io/search/#"${i.ioc}"`,
                        badgeClass: 'src-osint', icon: 'fas fa-eye', colorClass: 'text-indigo-400'
                    }), 'malware', 5);
                    
                    add('Botvrij.eu', this.data.botvrij, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Open Botnet', details: i.desc,
                        link: 'https://www.botvrij.eu', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-botvrij', icon: 'fas fa-robot', colorClass: 'text-teal-400'
                    }), 'botnet', 7);
                    
                    add('GreenSnow', this.data.greensnow, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Mass Brute Force', details: 'Attack Source',
                        link: 'https://blocklist.greensnow.co/', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-greensnow', icon: 'fas fa-snowflake', colorClass: 'text-lime-400'
                    }), 'network', 6);
                    
                    add('VX Vault', this.data.vxvault, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Malware URL', details: 'High Conf. Malware',
                        link: 'http://vxvault.net/URL_List.php', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-vxvault', icon: 'fas fa-bug', colorClass: 'text-fuchsia-400'
                    }), 'malware', 9);
                    
                    add('Phishing.Database', this.data.phishdb, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Phishing URL', details: 'Fresh Phish',
                        link: 'https://github.com/mitchellkrogza/Phishing.Database', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-phishdb', icon: 'fas fa-fish', colorClass: 'text-rose-400'
                    }), 'phishing', 8);
                    
                    add('CoinBlocker', this.data.coinblocker, i => ({
                        rawTime: i.date, ioc: i.domain, type: 'Crypto Mining', details: 'Cryptojacking Domain',
                        link: 'https://zerodot1.gitlab.io/CoinBlockerListsWeb/', pivotLink: `https://urlscan.io/search/#"${i.domain}"`,
                        badgeClass: 'src-coin', icon: 'fas fa-coins', colorClass: 'text-yellow-300'
                    }), 'crypto', 4);

                    add('EmergingThreats', this.data.et, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Compromised Host', details: 'ET Block Rules',
                        link: 'https://rules.emergingthreats.net', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-et', icon: 'fas fa-skull', colorClass: 'text-pink-400'
                    }), 'malware', 7);
                    
                    add('SSL Blacklist', this.data.sslbl, i => ({
                        rawTime: i.date, ioc: i.sha1, type: 'Malicious Cert', details: 'Abuse.ch SSLBL',
                        link: 'https://sslbl.abuse.ch', pivotLink: `https://censys.io/certificates?q=${i.sha1}`,
                        badgeClass: 'src-sslbl', icon: 'fas fa-lock', colorClass: 'text-teal-300'
                    }), 'botnet', 8);

                    add('BinaryDefense', this.data.binary, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Artillery Ban', details: 'Known Attacker',
                        link: 'https://www.binarydefense.com', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-binary', icon: 'fas fa-shield-alt', colorClass: 'text-indigo-300'
                    }), 'network', 6);

                    add('CINS Army', this.data.cins, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Bad Reputation', details: 'Sentinel/CI-BadGuys',
                        link: 'http://cinsscore.com', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-cins', icon: 'fas fa-fighter-jet', colorClass: 'text-red-300'
                    }), 'network', 7);

                    add('Spamhaus DROP', this.data.spamhaus, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Cybercrime Net', details: 'Don\'t Route/Peer',
                        link: 'https://www.spamhaus.org/drop/', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-spamhaus', icon: 'fas fa-ban', colorClass: 'text-slate-300'
                    }), 'network', 9);

                    add('Bambenek C2', this.data.bambenek, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'C2 Masterlist', details: 'Known Command & Control',
                        link: 'http://osint.bambenekconsulting.com/feeds/', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-bambenek', icon: 'fas fa-server', colorClass: 'text-fuchsia-400'
                    }), 'botnet', 10);
                    
                    add('StopForumSpam', this.data.stopforum, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Toxic IP', details: 'Forum Spammer',
                        link: 'https://www.stopforumspam.com', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-stopforum', icon: 'fas fa-comment-slash', colorClass: 'text-orange-300'
                    }), 'network', 5);
                    
                    add('Darklist.de', this.data.darklist, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'SSH/HTTP Attack', details: 'Darklist Aggregated',
                        link: 'https://darklist.de', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-darklist', icon: 'fas fa-spider', colorClass: 'text-slate-400'
                    }), 'network', 6);
                    
                    add('Open Proxies', this.data.proxies, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Open Proxy', details: 'Socks4/5 Anonymizer',
                        link: '#', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-proxy', icon: 'fas fa-mask', colorClass: 'text-teal-300'
                    }), 'all', 4);
                    
                    add('CyberCrime-Tracker', this.data.cybercrime, i => ({
                        rawTime: i.date, ioc: i.url, type: 'C2 Panel', details: 'Botnet Controller',
                        link: 'https://cybercrime-tracker.net', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-cybercrime', icon: 'fas fa-network-wired', colorClass: 'text-purple-400'
                    }), 'botnet', 10);
                    
                    add('URLVir', this.data.urlvir, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Malware Link', details: 'URLVir Feed',
                        link: 'http://www.urlvir.com/', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-urlvir', icon: 'fas fa-link', colorClass: 'text-pink-400'
                    }), 'malware', 7);
                    
                    add('PhishStats', this.data.phishstats, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Phishing', details: i.title,
                        link: 'https://phishstats.info', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-phishstats', icon: 'fas fa-fish', colorClass: 'text-rose-400'
                    }), 'phishing', 8);
                    
                    add('MalwareDomainList', this.data.mdl, i => ({
                        rawTime: i.date, ioc: i.domain, type: 'Malware Domain', details: i.desc,
                        link: 'http://www.malwaredomainlist.com/mdl.php', pivotLink: `https://urlscan.io/search/#"${i.domain}"`,
                        badgeClass: 'src-mdl', icon: 'fas fa-skull-crossbones', colorClass: 'text-purple-300'
                    }), 'malware', 8);
                    
                    add('Bambenek DGA', this.data.dga, i => ({
                        rawTime: i.date, ioc: i.domain, type: 'DGA Domain', details: i.desc,
                        link: 'http://osint.bambenekconsulting.com/feeds/', pivotLink: `https://urlscan.io/search/#"${i.domain}"`,
                        badgeClass: 'src-dga', icon: 'fas fa-random', colorClass: 'text-yellow-200'
                    }), 'botnet', 9);
                    
                    add('Blocklist.de Apache', this.data.apache, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Apache Attack', details: 'Web Exploit',
                        link: 'https://lists.blocklist.de/lists/apache.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-apache', icon: 'fas fa-server', colorClass: 'text-rose-300'
                    }), 'network', 7);
                    
                    add('Blocklist.de Mail', this.data.mail, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Mail Server Attack', details: 'Postfix/Exim Brute',
                        link: 'https://lists.blocklist.de/lists/mail.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-envelope', colorClass: 'text-orange-400'
                    }), 'network', 6);
                    
                    add('Blocklist.de FTP', this.data.ftp, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'FTP Attack', details: 'FTP Brute Force',
                        link: 'https://lists.blocklist.de/lists/ftp.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-file-upload', colorClass: 'text-amber-400'
                    }), 'network', 5);
                    
                    add('Blocklist.de IMAP', this.data.imap, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'IMAP Attack', details: 'Email Access Brute',
                        link: 'https://lists.blocklist.de/lists/imap.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-inbox', colorClass: 'text-yellow-500'
                    }), 'network', 5);
                    
                    add('Blocklist.de SIP', this.data.sip, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'SIP Attack', details: 'VoIP Gateway Abuse',
                        link: 'https://lists.blocklist.de/lists/sip.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-phone-slash', colorClass: 'text-red-400'
                    }), 'network', 6);
                    
                    add('Blocklist.de Bots', this.data.bots, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'RFI/Bot', details: 'Remote File Inclusion',
                        link: 'https://lists.blocklist.de/lists/bots.txt', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-blocklist', icon: 'fas fa-robot', colorClass: 'text-fuchsia-500'
                    }), 'botnet', 8);
                    
                    add('CleanMX', this.data.cleanmx, i => ({
                        rawTime: i.date, ioc: i.url, type: 'Virus/Malware', details: 'CleanMX VirusWatch',
                        link: 'http://lists.clean-mx.com/pipermail/viruswatch/', pivotLink: `https://urlscan.io/search/#"${i.url}"`,
                        badgeClass: 'src-cleanmx', icon: 'fas fa-virus', colorClass: 'text-teal-400'
                    }), 'malware', 9);
                    
                    add('CyberCure', this.data.cybercure, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Malicious IP', details: 'CyberCure Intel',
                        link: 'http://api.cybercure.ai/feed/get_ips', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-cybercure', icon: 'fas fa-biohazard', colorClass: 'text-rose-400'
                    }), 'network', 7);
                    
                    add('Rutgers', this.data.rutgers, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'Bad Actor', details: 'Rutgers Blacklist',
                        link: 'https://report.cs.rutgers.edu/DROP/attackers', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-rutgers', icon: 'fas fa-university', colorClass: 'text-purple-400'
                    }), 'network', 6);
                    
                    add('NIPR', this.data.nipr, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'DoD Blocklist', details: 'NIPR Intrusion',
                        link: '#', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-nipr', icon: 'fas fa-shield-alt', colorClass: 'text-blue-400'
                    }), 'network', 8);
                    
                    add('UCEPROTECT', this.data.uce, i => ({
                        rawTime: i.date, ioc: i.ip, type: 'L1 Spammer', details: 'UCEPROTECT Level 1',
                        link: 'http://www.uceprotect.net', pivotLink: `https://www.abuseipdb.com/check/${i.ip}`,
                        badgeClass: 'src-uce', icon: 'fas fa-mail-bulk', colorClass: 'text-yellow-400'
                    }), 'network', 5);

                    this.allSources = Array.from(seenSources).sort();
                    this.unified = combined.sort((a, b) => new Date(b.rawTime) - new Date(a.rawTime));
                },
                
                timeAgo(dateString) {
                    if (!dateString) return 'Unknown';
                    const date = new Date(dateString);
                    const now = new Date();
                    const seconds = Math.floor((now - date) / 1000);
                    
                    let interval = seconds / 31536000;
                    if (interval > 1) return Math.floor(interval) + " years ago";
                    interval = seconds / 2592000;
                    if (interval > 1) return Math.floor(interval) + " months ago";
                    interval = seconds / 86400;
                    if (interval > 1) return Math.floor(interval) + " days ago";
                    interval = seconds / 3600;
                    if (interval > 1) return Math.floor(interval) + " hrs ago";
                    interval = seconds / 60;
                    if (interval > 1) return Math.floor(interval) + " mins ago";
                    return Math.floor(seconds) + " secs ago";
                },
                
                formatDate(dateString) {
                     if (!dateString) return '';
                     return new Date(dateString).toLocaleString();
                },
                
                getRiskClass(score) {
                    if (score >= 9) return 'risk-crit';
                    if (score >= 7) return 'risk-high';
                    if (score >= 4) return 'risk-med';
                    return 'risk-low';
                },

                get filteredUnified() {
                    let list = this.unified;
                    
                    // Filter by Source Dropdown
                    if (this.selectedSource !== 'all') {
                        list = list.filter(item => item.source === this.selectedSource);
                    }
                    
                    // Filter by Chips
                    if (this.activeFilter === 'correlated') {
                        list = list.filter(item => item.correlated === true);
                    } else if (this.activeFilter !== 'all') {
                        list = list.filter(item => item.category === this.activeFilter);
                    }
                    
                    // Search Query
                    if (!this.searchQuery) return list;
                    const q = this.searchQuery.toLowerCase();
                    return list.filter(i => 
                        i.ioc.toLowerCase().includes(q) || 
                        i.type.toLowerCase().includes(q) || 
                        i.source.toLowerCase().includes(q) ||
                        i.details.toLowerCase().includes(q)
                    );
                },

                updateMetrics() {
                    const count = (arr) => arr ? arr.length : 0;
                    
                    const correlatedCount = this.unified.filter(i => i.correlated).length;
                    this.metrics[0].value = correlatedCount;
                    
                    this.metrics[1].value = count(this.data.sans) + count(this.data.binary) + count(this.data.cins) + count(this.data.spamhaus) + count(this.data.stopforum) + count(this.data.darklist) + count(this.data.apache) + count(this.data.mail) + count(this.data.ftp) + count(this.data.imap) + count(this.data.sip) + count(this.data.cybercure) + count(this.data.rutgers) + count(this.data.nipr) + count(this.data.uce);
                    this.metrics[2].value = count(this.data.feodo) + count(this.data.botvrij) + count(this.data.threatfox) + count(this.data.sslbl) + count(this.data.bambenek) + count(this.data.cybercrime) + count(this.data.dga) + count(this.data.bots);
                    this.metrics[3].value = count(this.data.urlhaus) + count(this.data.vxvault) + count(this.data.et) + count(this.data.osint) + count(this.data.urlvir) + count(this.data.mdl) + count(this.data.cleanmx);
                    this.metrics[4].value = count(this.data.openphish) + count(this.data.phishdb) + count(this.data.phishstats);
                    this.metrics[5].value = count(this.data.bazaar);
                    this.metrics[6].value = count(this.data.cisa);
                    this.metrics[7].value = count(this.data.osint);
                    this.metrics[8].value = count(this.data.tor) + count(this.data.proxies);
                    this.metrics[9].value = count(this.data.blocklist) + count(this.data.greensnow);
                    this.metrics[10].value = count(this.data.coinblocker);
                },

                renderMap() {
                    const counts = {};
                    if(this.data.sans) {
                        this.data.sans.forEach(i => {
                            if(i.country) counts[i.country] = (counts[i.country] || 0) + i.reports;
                        });
                    }
                    
                    if (Object.keys(counts).length === 0 && this.isSimulation) {
                        ['CN', 'RU', 'US', 'BR', 'IR', 'KP'].forEach(c => counts[c] = Math.floor(Math.random() * 100));
                    }
                    
                    const data = [{
                        type: 'choropleth',
                        locations: Object.keys(counts),
                        z: Object.values(counts),
                        colorscale: [[0, '#1e293b'], [1, '#ef4444']],
                        autocolorscale: false,
                        marker: { line: { color: '#334155', width: 0.5 } },
                        colorbar: { thickness: 10, len: 0.5, bg: '#0f172a', tickfont: {color: 'white'} }
                    }];

                    const layout = {
                        geo: {
                            projection: { type: 'orthographic' },
                            bgcolor: 'rgba(0,0,0,0)',
                            showocean: true, oceancolor: '#0f172a',
                            showland: true, landcolor: '#1e293b',
                            showlakes: false,
                            showcountries: true, countrycolor: '#334155',
                            coastlinecolor: '#475569'
                        },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        margin: { t: 0, l: 0, r: 0, b: 0 },
                        dragmode: 'orbit'
                    };
                    
                    Plotly.react('chart-map', data, layout, {displayModeBar: false});
                },

                renderRadar() {
                    const stats = { 'Malware': 0, 'Phishing': 0, 'Botnets': 0, 'Crypto': 0, 'Scanners': 0 };
                    
                    this.unified.forEach(u => {
                        const t = u.type.toLowerCase();
                        if(t.includes('malware') || t.includes('hash') || t.includes('compromised') || t.includes('virus')) stats['Malware']++;
                        else if(t.includes('phish')) stats['Phishing']++;
                        else if(t.includes('botnet') || t.includes('cert') || t.includes('c2') || t.includes('bot')) stats['Botnets']++;
                        else if(t.includes('crypto')) stats['Crypto']++;
                        else stats['Scanners']++;
                    });
                    
                    const maxVal = Math.max(...Object.values(stats)) || 1;
                    
                    const data = [{
                        type: 'scatterpolar',
                        r: Object.values(stats),
                        theta: Object.keys(stats),
                        fill: 'toself',
                        fillcolor: 'rgba(59, 130, 246, 0.2)',
                        line: { color: '#60a5fa' }
                    }];

                    const layout = {
                        polar: {
                            radialaxis: { visible: true, range: [0, maxVal * 1.1], gridcolor: '#334155', tickfont: {color: '#94a3b8'} },
                            angularaxis: { tickfont: { color: 'white', size: 10 }, gridcolor: '#334155' },
                            bgcolor: 'rgba(0,0,0,0)'
                        },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        margin: { t: 20, b: 20, l: 40, r: 40 },
                        showlegend: false
                    };
                    
                    Plotly.react('chart-radar', data, layout, {displayModeBar: false});
                },

                togglePause() {
                    this.isPaused = !this.isPaused;
                    this.statusText = this.isPaused ? 'FEED PAUSED' : 'RESUMING...';
                    if (!this.isPaused) this.fetchData();
                },
                
                toggleSimulation() {
                    this.isSimulation = !this.isSimulation;
                    this.fetchData();
                },
                
                copy(text) {
                    navigator.clipboard.writeText(text).then(() => {
                        // Fixed regex logic by using double escape in Python string r"" not needed
                        // Since we use r"" string, we just write normal regex.
                        const type = text.includes('.') && !text.match(/^\\d/) ? 'URL/Domain' : (text.length > 30 ? 'Hash' : 'IP');
                        this.showToast(`Copied ${type}: ${text}`);
                    });
                },
                
                showToast(message) {
                    const id = Date.now();
                    this.toasts.push({ id, message, visible: true });
                    setTimeout(() => {
                        this.toasts = this.toasts.filter(t => t.id !== id);
                    }, 3000);
                },

                exportJSON() {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.unified, null, 2));
                    this.downloadFile(dataStr, "hunters_gaze_export.json");
                },

                exportCSV() {
                    let csvContent = "data:text/csv;charset=utf-8,Source,Time,IOC,Type,Risk,Details\\n";
                    this.unified.forEach(row => {
                        csvContent += `${row.source},${row.rawTime},${row.ioc},${row.type},${row.risk},"${row.details}"\\n`;
                    });
                    this.downloadFile(csvContent, "hunters_gaze_export.csv");
                },
                
                exportSTIX() {
                    const bundle = {
                        type: "bundle",
                        id: "bundle--" + crypto.randomUUID(),
                        objects: this.unified.map(item => ({
                            type: "indicator",
                            id: "indicator--" + crypto.randomUUID(),
                            created: new Date().toISOString(),
                            modified: new Date().toISOString(),
                            name: item.type,
                            description: item.details,
                            pattern: item.ioc.includes('.') ? `[domain-name:value = '${item.ioc}']` : `[ipv4-addr:value = '${item.ioc}']`,
                            pattern_type: "stix",
                            valid_from: new Date().toISOString(),
                            labels: [item.category, item.source]
                        }))
                    };
                    const dataStr = "data:application/json;charset=utf-8," + encodeURIComponent(JSON.stringify(bundle, null, 2));
                    this.downloadFile(dataStr, "hunters_gaze_stix2.json");
                },

                downloadFile(content, fileName) {
                    const link = document.createElement('a');
                    link.setAttribute("href", content);
                    link.setAttribute("download", fileName);
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                },

                init() {
                    this.fetchData();
                    setInterval(() => this.fetchData(), 60000);
                }
            }))
        })
    </script>
</body>
</html>
"""

# --- HELPERS ---

def fetch_with_timeout(url, timeout=3): # Reduced timeout for faster fallback
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response
    except Exception as e:
        return None

# --- MOCK DATA GENERATOR (Fallback) ---
def generate_mock_data():
    """Generates realistic threat data when APIs fail"""
    print("⚠️  Live Feeds Unreachable. Switching to Simulation Mode.")
    
    mock_ips = [f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}" for _ in range(60)]
    mock_domains = ["malicious-server.com", "phishing-bank-login.net", "crypto-miner-pool.xyz", "botnet-c2-node.org", "update-security-patch.com"]
    countries = ['CN', 'RU', 'US', 'IR', 'KP', 'BR']
    
    now = datetime.now(timezone.utc).isoformat()
    
    data = {
        "simulation": True,
        "sans": [{"ip": ip, "reports": random.randint(10, 5000), "country": random.choice(countries), "updated": now} for ip in mock_ips[:10]],
        "urlhaus": [{"date": now, "url": f"http://{d}/payload.exe", "status": "online", "threat": "malware_download", "link": "#"} for d in mock_domains],
        "threatfox": [{"date": now, "ioc": mock_ips[11], "threat_type": "botnet_cc", "malware": "Cobalt Strike", "reference": "#", "reporter": "admin"}],
        "cisa": [{"dateAdded": now, "cveID": "CVE-2024-9999", "product": "Simulation OS", "shortDescription": "Critical RCE in kernel.", "requiredAction": "Patch immediately"}],
        "feodo": [{"date": now, "ip": mock_ips[12], "port": "443", "malware": "Emotet"}],
        "bazaar": [{"date": now, "hash": "a1b2c3d4e5f6...", "type": "exe", "signature": "Ransomware.LockBit", "link": "#"}],
        "osint": [{"ioc": d} for d in mock_domains],
        "openphish": [{"url": f"http://{d}/login"} for d in mock_domains],
        "tor": [{"ip": ip, "date": now} for ip in mock_ips[13:18]],
        "blocklist": [{"ip": ip, "date": now} for ip in mock_ips[19:25]],
        "botvrij": [{"ip": ip, "date": now, "desc": "Botnet Node"} for ip in mock_ips[26:30]],
        "greensnow": [{"ip": ip, "date": now} for ip in mock_ips[31:35]],
        "vxvault": [{"url": f"http://{mock_domains[0]}/virus.zip", "date": now}],
        "phishdb": [{"url": f"http://{mock_domains[1]}/secure", "date": now}],
        "coinblocker": [{"domain": "miner.pool.com", "date": now}],
        "et": [{"ip": mock_ips[36], "date": now}],
        "sslbl": [{"date": now, "sha1": "123456789abcdef...", "reason": "Dridex Cert"}],
        "binary": [{"ip": mock_ips[37], "date": now}],
        "cins": [{"ip": mock_ips[38], "date": now}],
        "spamhaus": [{"ip": mock_ips[39], "date": now}],
        "bambenek": [{"ip": mock_ips[40], "date": now}],
        "stopforum": [{"ip": mock_ips[41], "date": now}],
        "darklist": [{"ip": mock_ips[42], "date": now}],
        "proxies": [{"ip": mock_ips[43], "date": now}],
        "cybercrime": [{"url": f"http://{mock_domains[2]}/panel", "date": now}],
        "urlvir": [{"url": f"http://{mock_domains[3]}/dropper", "date": now}],
        "phishstats": [{"url": f"http://{mock_domains[4]}/verify", "title": "Fake Login", "date": now}],
        "mdl": [{"domain": "bad-site.com", "desc": "Malware Host", "date": now}],
        "dga": [{"domain": "axbycz123.com", "desc": "Gameover Zeus", "date": now}],
        "apache": [{"ip": mock_ips[44], "date": now}],
        "mail": [{"ip": mock_ips[45], "date": now}],
        "ftp": [{"ip": mock_ips[46], "date": now}],
        "imap": [{"ip": mock_ips[47], "date": now}],
        "sip": [{"ip": mock_ips[48], "date": now}],
        "bots": [{"ip": mock_ips[49], "date": now}],
        "cleanmx": [{"url": "http://virus-source.net/bin", "date": now}],
        "cybercure": [{"ip": mock_ips[50], "date": now}],
        "rutgers": [{"ip": mock_ips[51], "date": now}],
        "nipr": [{"ip": mock_ips[52], "date": now}],
        "uce": [{"ip": mock_ips[53], "date": now}]
    }
    return data

# --- BACKEND FETCHERS (Updated with Headers & Timeout Handling) ---

def get_sans():
    resp = fetch_with_timeout("https://isc.sans.edu/api/sources/attacks/20/?json")
    if not resp: return []
    try:
        data = resp.json()
        attacks = data if isinstance(data, list) else data.get('attacks', [])
        return [{'ip': a.get('ip'), 'reports': a.get('reports'), 'country': a.get('country'), 'updated': a.get('updated', datetime.now(timezone.utc).isoformat())} for a in attacks]
    except: return []

def get_urlhaus():
    resp = fetch_with_timeout("https://urlhaus.abuse.ch/feeds/recent/")
    if not resp: return [], {}
    try:
        lines = [l for l in resp.text.splitlines() if not l.startswith('#')][:40]
        processed = []
        tags_list = []
        for l in lines:
            p = l.split('","')
            if len(p) > 7:
                clean = [x.replace('"', '') for x in p]
                processed.append({'date': clean[1], 'url': clean[2], 'status': clean[3], 'threat': clean[5], 'link': clean[7]})
                tags_list.extend([t.strip() for t in clean[6].split(',') if t.strip()])
        return processed, pd.Series(tags_list).value_counts().head(8).to_dict()
    except: return [], {}

def get_threatfox():
    resp = fetch_with_timeout("https://threatfox.abuse.ch/export/csv/recent/")
    if not resp: return []
    try:
        f = io.StringIO(resp.text)
        reader = csv.reader(filter(lambda x: not x.startswith('#'), f))
        processed = []
        for i, row in enumerate(reader):
            if i >= 30: break
            if len(row) > 13:
                processed.append({'date': row[0], 'ioc': row[2], 'threat_type': row[4], 'malware': row[7], 'reference': row[10], 'reporter': row[13]})
        return processed
    except: return []

def get_feodo():
    resp = fetch_with_timeout("https://feodotracker.abuse.ch/downloads/ipblocklist.json")
    if not resp: return []
    try:
        data = resp.json()
        processed = []
        for item in data[:30]:
            processed.append({'date': item.get('first_seen_utc'), 'ip': item.get('ip_address'), 'port': item.get('dst_port'), 'malware': item.get('malware')})
        return processed
    except: return []

def get_bazaar():
    resp = fetch_with_timeout("https://bazaar.abuse.ch/export/csv/recent/")
    if not resp: return []
    try:
        lines = [l for l in resp.text.splitlines() if not l.startswith('#')][:30]
        processed = []
        for l in lines:
            p = l.split('","')
            if len(p) > 8:
                clean = [x.replace('"', '') for x in p]
                processed.append({'date': clean[0], 'hash': clean[1], 'type': clean[2], 'size': clean[3], 'signature': clean[4], 'link': f"https://bazaar.abuse.ch/sample/{clean[1]}/"})
        return processed
    except: return []

def get_cisa_kev():
    resp = fetch_with_timeout("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    if not resp: return []
    try:
        data = resp.json()
        vulns = data.get('vulnerabilities', [])
        vulns.sort(key=lambda x: x['dateAdded'], reverse=True)
        return vulns[:20]
    except: return []

# Simple Text List Fetchers
def get_text_list(url, key_name, limit=30, parse_func=None):
    resp = fetch_with_timeout(url)
    if not resp: return []
    try:
        lines = [l.strip() for l in resp.text.splitlines() if l.strip() and not l.startswith(('#', ';', '<'))]
        processed = []
        now = datetime.now(timezone.utc).isoformat()
        for l in lines[:limit]:
            if parse_func:
                val = parse_func(l)
                if val: processed.append({key_name: val, "date": now})
            else:
                processed.append({key_name: l, "date": now})
        return processed
    except: return []

def get_mdl():
    """Malware Domain List (CSV)"""
    resp = fetch_with_timeout("http://www.malwaredomainlist.com/mdlcsv.php")
    if not resp: return []
    try:
        lines = [l for l in resp.text.splitlines() if l.strip()]
        processed = []
        now = datetime.now(timezone.utc).isoformat()
        for l in lines[:30]:
            parts = l.split('","')
            if len(parts) > 4:
                domain = parts[1].replace('"', '')
                desc = parts[4].replace('"', '')
                processed.append({"domain": domain, "desc": desc, "date": now})
        return processed
    except: return []

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def api_data():
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            "sans": executor.submit(get_sans),
            "urlhaus": executor.submit(get_urlhaus),
            "threatfox": executor.submit(get_threatfox),
            "feodo": executor.submit(get_feodo),
            "bazaar": executor.submit(get_bazaar),
            "cisa": executor.submit(get_cisa_kev),
            "osint": executor.submit(get_text_list, "https://osint.digitalside.it/threat-intel/lists/latestdomains.txt", "ioc"),
            "openphish": executor.submit(get_text_list, "https://openphish.com/feed.txt", "url"),
            "tor": executor.submit(get_text_list, "https://check.torproject.org/torbulkexitlist", "ip"),
            "blocklist": executor.submit(get_text_list, "https://lists.blocklist.de/lists/ssh.txt", "ip"),
            "botvrij": executor.submit(get_text_list, "https://www.botvrij.eu/data/ioclist.ip-v4", "ip"),
            "greensnow": executor.submit(get_text_list, "https://blocklist.greensnow.co/greensnow.txt", "ip"),
            "vxvault": executor.submit(get_text_list, "http://vxvault.net/URL_List.php", "url"),
            "phishdb": executor.submit(get_text_list, "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-NEW-today.txt", "url"),
            "coinblocker": executor.submit(get_text_list, "https://raw.githubusercontent.com/ZeroDot1/CoinBlockerLists/master/list_browser.txt", "domain"),
            "et": executor.submit(get_text_list, "https://rules.emergingthreats.net/blockrules/compromised-ips.txt", "ip"),
            "sslbl": executor.submit(get_text_list, "https://sslbl.abuse.ch/blacklist/sslblacklist.csv", "sha1", lambda l: l.split(',')[1] if ',' in l else None),
            "binary": executor.submit(get_text_list, "https://www.binarydefense.com/banlist.txt", "ip"),
            "cins": executor.submit(get_text_list, "http://cinsscore.com/list/ci-badguys.txt", "ip"),
            "spamhaus": executor.submit(get_text_list, "https://www.spamhaus.org/drop/drop.txt", "ip", lambda l: l.split(';')[0].strip()),
            "bambenek": executor.submit(get_text_list, "http://osint.bambenekconsulting.com/feeds/c2-ipmasterlist.txt", "ip", lambda l: l.split(',')[0]),
            "stopforum": executor.submit(get_text_list, "https://www.stopforumspam.com/downloads/toxic_ip_cidr.txt", "ip"),
            "darklist": executor.submit(get_text_list, "https://darklist.de/raw.php", "ip"),
            "proxies": executor.submit(get_text_list, "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", "ip", lambda l: l.split(':')[0]),
            "cybercrime": executor.submit(get_text_list, "https://cybercrime-tracker.net/all.php", "url"),
            "urlvir": executor.submit(get_text_list, "http://www.urlvir.com/export-hosts/", "url"),
            "phishstats": executor.submit(get_text_list, "https://phishstats.info/phish_score.csv", "url", lambda l: l.split(',')[2].strip('"') if len(l.split(',')) > 2 and not l.startswith('#') else None),
            "mdl": executor.submit(get_mdl),
            "dga": executor.submit(get_text_list, "http://osint.bambenekconsulting.com/feeds/dga-feed.txt", "domain", lambda l: l.split(',')[0] if ',' in l else None),
            "apache": executor.submit(get_text_list, "https://lists.blocklist.de/lists/apache.txt", "ip"),
            "mail": executor.submit(get_text_list, "https://lists.blocklist.de/lists/mail.txt", "ip"),
            "ftp": executor.submit(get_text_list, "https://lists.blocklist.de/lists/ftp.txt", "ip"),
            "imap": executor.submit(get_text_list, "https://lists.blocklist.de/lists/imap.txt", "ip"),
            "sip": executor.submit(get_text_list, "https://lists.blocklist.de/lists/sip.txt", "ip"),
            "bots": executor.submit(get_text_list, "https://lists.blocklist.de/lists/bots.txt", "ip"),
            "cleanmx": executor.submit(get_text_list, "http://lists.clean-mx.com/pipermail/viruswatch/", "url"), # Placeholder scrape
            "cybercure": executor.submit(get_text_list, "http://api.cybercure.ai/feed/get_ips", "ip"),
            "rutgers": executor.submit(get_text_list, "https://report.cs.rutgers.edu/DROP/attackers", "ip"),
            "nipr": executor.submit(get_text_list, "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/nipr_iscs.ipset", "ip"),
            "uce": executor.submit(get_text_list, "http://wget-mirrors.uceprotect.net/rbldnsd-all/dnsbl-1.uceprotect.net.gz", "ip") # Simplified
        }

        results = {}
        has_data = False
        for key, future in futures.items():
            try:
                res = future.result()
                if res and (isinstance(res, list) and len(res) > 0) or (isinstance(res, tuple) and len(res[0]) > 0):
                    has_data = True
                results[key] = res
            except Exception as e:
                results[key] = []

        # --- AUTO-FAILOVER TO MOCK DATA ---
        if not has_data:
            return jsonify(generate_mock_data())

        # Handle tuple return from urlhaus
        if isinstance(results["urlhaus"], tuple):
             urlhaus_data, urlhaus_tags = results["urlhaus"]
             results["urlhaus"] = urlhaus_data
             results["urlhaus_tags"] = urlhaus_tags
        else:
             results["urlhaus_tags"] = {}

        # --- Cross-Correlation Logic ---
        all_iocs = []
        for key, data in results.items():
            if isinstance(data, list):
                for item in data:
                    ioc = item.get('ip') or item.get('url') or item.get('domain') or item.get('hash') or item.get('cveID') or item.get('sha1')
                    if ioc: all_iocs.append(ioc)
        
        ioc_counts = Counter(all_iocs)
        
        for key, data in results.items():
            if isinstance(data, list):
                for item in data:
                    ioc = item.get('ip') or item.get('url') or item.get('domain') or item.get('hash') or item.get('cveID') or item.get('sha1')
                    if ioc and ioc_counts[ioc] > 1:
                        item['correlated'] = True

        return jsonify(results)

if __name__ == '__main__':
    print("\n🛡️  HUNTER'S GAZE XL-SOC ONLINE")
    print("👉 ACCESS: http://127.0.0.1:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
