import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';

// Weight configuration
const weightConfig = {
  commute: { label: "Commute", icon: "🚇" },
  safety: { label: "Safety", icon: "🛡️" },
  noise: { label: "Quiet", icon: "🔇" },
  amenities: { label: "Amenities", icon: "🏪" },
  greenSpace: { label: "Green Space", icon: "🌳" },
  jobs: { label: "Jobs", icon: "💼" },
  education: { label: "Education", icon: "📚" },
  political: { label: "Political", icon: "🗳️" }
};

// API Base URL - change this for production
const API_BASE = 'http://localhost:8000';

// Generate deterministic scores (fallback for demo)
const generateScores = (ntaCode) => {
  const seed = ntaCode?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) || 0;
  const random = (offset) => ((seed + offset) % 100) / 100 * 0.5 + 0.4;
  return {
    commute: random(1), safety: random(2), noise: random(3), amenities: random(4),
    greenSpace: random(5), jobs: random(6), education: random(7), political: random(8)
  };
};

// Calculate weighted score
const calculateScore = (scores, weights) => {
  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);
  let score = 0;
  Object.keys(weights).forEach(key => {
    score += (weights[key] / totalWeight) * (scores[key] || 0.5);
  });
  return score;
};

// Map controller
function MapController({ selected }) {
  const map = useMap();
  useEffect(() => {
    if (selected?.center) {
      map.flyTo(selected.center, 13, { duration: 0.8 });
    }
  }, [selected, map]);
  return null;
}

export default function RentSenseMap() {
  const [ntaData, setNtaData] = useState(null);
  const [userWeights, setUserWeights] = useState({
    commute: 1, safety: 1, noise: 1, amenities: 1,
    greenSpace: 1, jobs: 1, education: 1, political: 1
  });
  const [selectedNeighborhood, setSelectedNeighborhood] = useState(null);
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [geoJsonKey, setGeoJsonKey] = useState(0);
  const [hoveredCard, setHoveredCard] = useState(null);
  
  // Budget slider state
  const [budgetMin, setBudgetMin] = useState(1500);
  const [budgetMax, setBudgetMax] = useState(5000);
  
  // Chat state - connected to backend
  const [showChat, setShowChat] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Backend conversation state
  const [conversationHistory, setConversationHistory] = useState([]);
  const [questionsAsked, setQuestionsAsked] = useState(0);
  const [dimensionsCovered, setDimensionsCovered] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [backendResults, setBackendResults] = useState(null);
  const [mode, setMode] = useState('discovery'); // 'discovery' or 'migration'

  useEffect(() => {
    fetch('/nta.geojson')
      .then(res => res.json())
      .then(data => {
        setNtaData(data);
        // Only include actual neighborhoods (ntatype 0), not parks/cemeteries/etc
        const hoods = data.features
          .filter(f => f.properties.ntatype === "0")
          .map(f => {
            const scores = generateScores(f.properties.nta2020);
            const coords = f.geometry.type === 'MultiPolygon' 
              ? f.geometry.coordinates[0][0]
              : f.geometry.coordinates[0];
            const center = coords && coords.length > 0 ? [
              coords.reduce((sum, c) => sum + c[1], 0) / coords.length,
              coords.reduce((sum, c) => sum + c[0], 0) / coords.length
            ] : [40.7128, -74.006];
            return {
              id: f.properties.nta2020,
              name: f.properties.ntaname,
              borough: f.properties.boroname,
              scores, center,
              rent: 1500 + Math.floor(Math.random() * 3500),
              listings: 10 + Math.floor(Math.random() * 50)
            };
          });
        setNeighborhoods(hoods);
      })
      .catch(err => console.error('Error loading GeoJSON:', err));
  }, []);

  useEffect(() => {
    if (neighborhoods.length > 0) setGeoJsonKey(prev => prev + 1);
  }, [userWeights]);

  const getColor = (score) => {
    if (score > 0.8) return '#059669';
    if (score > 0.7) return '#10b981';
    if (score > 0.6) return '#34d399';
    if (score > 0.5) return '#6ee7b7';
    return '#a7f3d0';
  };

  const getStyle = (feature) => {
    const scores = generateScores(feature.properties.nta2020);
    const score = calculateScore(scores, userWeights);
    return {
      fillColor: getColor(score),
      weight: 2,
      opacity: 1,
      color: '#fff',
      fillOpacity: 0.8
    };
  };

  const onEachFeature = (feature, layer) => {
    const scores = generateScores(feature.properties.nta2020);
    const score = calculateScore(scores, userWeights);
    
    const ntaName = feature.properties.ntaname;
    const boroName = feature.properties.boroname || '';
    
    layer.bindTooltip(`
      <div style="font-family: system-ui, sans-serif; padding: 8px; min-width: 150px;">
        <div style="font-weight: 700; font-size: 16px; color: #1f2937; margin-bottom: 4px;">${ntaName}</div>
        <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">${boroName}</div>
        <div style="font-size: 28px; font-weight: 800; color: #059669;">${(score * 100).toFixed(1)}</div>
        <div style="font-size: 12px; color: #9ca3af;">Match Score</div>
      </div>
    `, { permanent: false, className: 'custom-tooltip' });

    layer.on({
      click: () => {
        const hood = neighborhoods.find(n => n.id === feature.properties.nta2020);
        if (hood) setSelectedNeighborhood(hood);
      }
    });
  };

  // Filter by budget and sort - use backend results if available
  const sortedNeighborhoods = React.useMemo(() => {
    if (backendResults && backendResults.length > 0) {
      return backendResults.map((r, i) => {
        // Try to find matching neighborhood from GeoJSON for coordinates
        const ntaCode = r.nta2020 || r.NTA2020 || '';
        const matchedHood = neighborhoods.find(n => n.id === ntaCode);
        
        return {
          id: ntaCode || `result-${i}`,
          name: r.ntaname || r.NTAName || r.neighborhood || 'Unknown',
          borough: r.boroname || r.Borough || r.borough || 'NYC',
          totalScore: r.fit_index || r.score || 0,
          rent: r.median_rent || r.rent || 3500,
          listings: r.listings || 30,
          center: matchedHood?.center || [40.7128, -74.006],
          scores: {
            commute: r.commute_score || 0.7,
            safety: r.safety_score || 0.7,
            noise: r.quiet_score || 0.7,
            amenities: r.amenities_score || 0.7,
            greenSpace: r.parks_score || 0.7,
            jobs: r.jobs_score || 0.7,
            education: r.schools_score || 0.7,
            political: r.politics_score || 0.7
          }
        };
      });
    }
    
    return [...neighborhoods]
      .map(n => ({ ...n, totalScore: calculateScore(n.scores, userWeights) }))
      .filter(n => n.rent >= budgetMin && n.rent <= budgetMax)
      .sort((a, b) => b.totalScore - a.totalScore)
      .slice(0, 10);
  }, [backendResults, neighborhoods, userWeights, budgetMin, budgetMax]);

  // Map frontend weight names to backend format
  const mapToBackendWeights = (weights) => {
    return {
      "Commute Convenience": weights.commute || 1,
      "Safety": weights.safety || 1,
      "Noise": weights.noise || 1,
      "Amenity Convenience": weights.amenities || 1,
      "Green Space Accessibility": weights.greenSpace || 1,
      "Job Opportunities": weights.jobs || 1,
      "Education Access": weights.education || 1,
      "Political Leaning": weights.political || 1
    };
  };

  // ============================================================
  // BACKEND API INTEGRATION
  // ============================================================
  const callBackendAPI = async (payload) => {
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Backend API Error:', error);
      throw error;
    }
  };

  // Handle initial user message
  const handleChat = async () => {
    if (!chatInput.trim() || isLoading) return;
    
    const userMessage = chatInput;
    setChatInput('');
    setIsLoading(true);
    
    // Add user message to chat
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const payload = {
        user_input: userMessage,
        selected_options: null,
        last_question_data: null,
        mode: mode,
        weights: mapToBackendWeights(userWeights),
        conversation_history: conversationHistory,
        questions_asked: questionsAsked,
        dimensions_covered: dimensionsCovered
      };

      const data = await callBackendAPI(payload);
      handleBackendResponse(data);
      
    } catch (error) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, there was an error connecting to the server. Make sure the backend is running on localhost:8000' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle MCQ option selection (single select)
  const handleOptionSelect = (optionId) => {
    setSelectedOptions([optionId]); // Single select - replace instead of toggle
  };

  // Submit selected MCQ options
  const submitOptions = async () => {
    if (selectedOptions.length === 0 || isLoading) return;
    
    setIsLoading(true);
    
    // Add user selection to chat
    const selectedLabels = selectedOptions.join(', ');
    
    setChatMessages(prev => [...prev, { role: 'user', content: selectedLabels }]);

    try {
      const payload = {
        user_input: null,
        selected_options: selectedOptions,
        last_question_data: currentQuestion,
        mode: mode,
        weights: mapToBackendWeights(userWeights),
        conversation_history: conversationHistory,
        questions_asked: questionsAsked,
        dimensions_covered: dimensionsCovered
      };

      const data = await callBackendAPI(payload);
      setSelectedOptions([]); // Reset selections
      handleBackendResponse(data);
      
    } catch (error) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, there was an error. Please try again.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Map backend dimension names to frontend names
  const mapBackendWeights = (weights) => {
    const mapping = {
      "Commute Convenience": "commute",
      "Safety": "safety",
      "Noise": "noise",
      "Amenity Convenience": "amenities",
      "Green Space Accessibility": "greenSpace",
      "Job Opportunities": "jobs",
      "Education Access": "education",
      "Political Leaning": "political",
      // Also handle if already in frontend format
      "commute": "commute",
      "safety": "safety",
      "noise": "noise",
      "amenities": "amenities",
      "greenSpace": "greenSpace",
      "jobs": "jobs",
      "education": "education",
      "political": "political"
    };
    
    const mapped = {
      commute: 1, safety: 1, noise: 1, amenities: 1,
      greenSpace: 1, jobs: 1, education: 1, political: 1
    };
    
    Object.entries(weights).forEach(([key, value]) => {
      const frontendKey = mapping[key];
      if (frontendKey) {
        mapped[frontendKey] = value;
      }
    });
    
    return mapped;
  };

  // Handle backend response
  const handleBackendResponse = (data) => {
    // Map weights from backend format to frontend format
    const mappedWeights = mapBackendWeights(data.weights);
    setUserWeights(mappedWeights);
    
    setConversationHistory(data.conversation_history);
    setQuestionsAsked(data.questions_asked);
    setDimensionsCovered(data.dimensions_covered);

    if (data.next_step === 'ask_question' && data.question) {
      // Show the question
      setCurrentQuestion(data.question);
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.question.question,
        isQuestion: true
      }]);
    } else if (data.next_step === 'show_results' && data.results) {
      // Show results
      setBackendResults(data.results);
      setCurrentQuestion(null);
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Based on your preferences, I found your top matches! Check the map and listings panel for your personalized recommendations.` 
      }]);
    }
  };

  // Reset conversation
  const resetConversation = () => {
    setChatMessages([]);
    setConversationHistory([]);
    setQuestionsAsked(0);
    setDimensionsCovered([]);
    setCurrentQuestion(null);
    setSelectedOptions([]);
    setBackendResults(null);
    setUserWeights({
      commute: 1, safety: 1, noise: 1, amenities: 1,
      greenSpace: 1, jobs: 1, education: 1, political: 1
    });
  };

  // Loading state
  if (!ntaData) {
    return (
      <div style={{
        height: '100vh',
        background: '#f9fafb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif"
      }}>
        <div style={{ textAlign: 'center' }}>
          <img 
            src="/logo.png" 
            alt="RentSense" 
            style={{ width: '80px', height: '80px', marginBottom: '24px' }} 
          />
          <h1 style={{ fontSize: '32px', fontWeight: '700', color: '#059669', margin: '0 0 12px' }}>RentSense</h1>
          <p style={{ color: '#6b7280', fontSize: '18px' }}>Loading NYC neighborhoods...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: '#f9fafb',
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif"
    }}>
      {/* HEADER */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 32px',
        background: '#fff',
        borderBottom: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <img 
            src="/logo.png" 
            alt="RentSense Logo" 
            style={{ width: '44px', height: '44px' }} 
          />
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '700', color: '#059669', margin: 0 }}>RentSense</h1>
            <p style={{ fontSize: '13px', color: '#6b7280', margin: 0 }}>Find your perfect NYC neighborhood</p>
          </div>
        </div>

        {/* Budget Slider + Chat Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          {/* Budget Slider */}
          <div style={{
            padding: '12px 20px',
            background: '#f9fafb',
            borderRadius: '12px',
            border: '1px solid #e5e7eb'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', color: '#6b7280' }}>Budget</span>
              <span style={{ fontSize: '16px', fontWeight: '700', color: '#1f2937' }}>
                ${budgetMin.toLocaleString()} — ${budgetMax.toLocaleString()}
              </span>
              <span style={{ fontSize: '13px', color: '#9ca3af' }}>per month</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '12px', color: '#9ca3af', width: '35px' }}>Min</span>
              <input
                type="range"
                min="500"
                max="10000"
                step="100"
                value={budgetMin}
                onChange={(e) => setBudgetMin(Math.min(Number(e.target.value), budgetMax - 500))}
                style={{ width: '120px', accentColor: '#059669', cursor: 'pointer' }}
              />
              <span style={{ fontSize: '12px', color: '#9ca3af', width: '35px' }}>Max</span>
              <input
                type="range"
                min="500"
                max="10000"
                step="100"
                value={budgetMax}
                onChange={(e) => setBudgetMax(Math.max(Number(e.target.value), budgetMin + 500))}
                style={{ width: '120px', accentColor: '#059669', cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Chat Button */}
          <button
            onClick={() => setShowChat(!showChat)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 20px',
              background: showChat ? '#059669' : '#fff',
              border: '1px solid #059669',
              borderRadius: '12px',
              color: showChat ? '#fff' : '#059669',
              fontSize: '15px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            Chat
          </button>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* MAP SECTION */}
        <div style={{ flex: 1, position: 'relative' }}>
          <MapContainer 
            center={[40.7128, -73.95]} 
            zoom={11} 
            style={{ width: '100%', height: '100%' }} 
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; CARTO'
              url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            />
            {ntaData && (
              <GeoJSON 
                key={geoJsonKey} 
                data={{
                  ...ntaData,
                  features: ntaData.features.filter(f => f.properties.ntatype === "0")
                }} 
                style={getStyle} 
                onEachFeature={onEachFeature} 
              />
            )}
            <MapController selected={selectedNeighborhood} />
          </MapContainer>

          {/* PREFERENCES PANEL */}
          <div style={{
            position: 'absolute',
            top: '20px',
            left: '20px',
            width: '280px',
            padding: '24px',
            background: '#fff',
            borderRadius: '16px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            border: '1px solid #e5e7eb',
            zIndex: 1000
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700', color: '#1f2937', margin: 0 }}>
                Your Preferences
              </h3>
              {questionsAsked > 0 && (
                <span style={{ 
                  fontSize: '11px', 
                  color: '#059669', 
                  background: '#ecfdf5', 
                  padding: '4px 8px', 
                  borderRadius: '6px',
                  fontWeight: '600'
                }}>
                  {questionsAsked}/4 questions
                </span>
              )}
            </div>
            <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 20px' }}>
              {questionsAsked > 0 ? 'Updated from your answers' : 'Use chat to personalize'}
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {Object.entries(userWeights).map(([key, value]) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '20px', width: '32px' }}>{weightConfig[key]?.icon || '📊'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '15px', color: '#374151', fontWeight: '500' }}>
                        {weightConfig[key]?.label || key}
                      </span>
                      <span style={{ 
                        fontSize: '15px', 
                        fontWeight: '700',
                        color: value > 1.2 ? '#059669' : value < 0.8 ? '#dc2626' : '#6b7280'
                      }}>{value.toFixed(2)}</span>
                    </div>
                    <div style={{
                      height: '8px',
                      background: '#e5e7eb',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${Math.min((value / 2) * 100, 100)}%`,
                        height: '100%',
                        background: '#059669',
                        borderRadius: '4px',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* LEGEND */}
          <div style={{
            position: 'absolute',
            bottom: '24px',
            left: '20px',
            padding: '16px 20px',
            background: '#fff',
            borderRadius: '12px',
            boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
            border: '1px solid #e5e7eb',
            zIndex: 1000
          }}>
            <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '10px', fontWeight: '600' }}>
              Match Score
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '13px', color: '#9ca3af' }}>Lower</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                {['#a7f3d0', '#6ee7b7', '#34d399', '#10b981', '#059669'].map((color, i) => (
                  <div key={i} style={{
                    width: '24px',
                    height: '12px',
                    background: color,
                    borderRadius: '2px'
                  }} />
                ))}
              </div>
              <span style={{ fontSize: '13px', color: '#9ca3af' }}>Higher</span>
            </div>
          </div>

          {/* CHAT PANEL - Connected to FastAPI */}
          {showChat && (
            <div style={{
              position: 'absolute',
              bottom: '24px',
              right: '24px',
              width: '420px',
              height: '500px',
              background: '#fff',
              borderRadius: '20px',
              boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
              border: '1px solid #e5e7eb',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              zIndex: 1000
            }}>
              {/* Chat Header */}
              <div style={{
                padding: '20px',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <h4 style={{ fontSize: '18px', fontWeight: '700', color: '#1f2937', margin: 0 }}>
                    AI Preference Assistant
                  </h4>
                  <p style={{ fontSize: '13px', color: '#6b7280', margin: '4px 0 0' }}>
                    {questionsAsked === 0 ? 'Describe what matters to you' : `Question ${questionsAsked} of 4`}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {questionsAsked > 0 && (
                    <button
                      onClick={resetConversation}
                      style={{
                        padding: '8px 12px',
                        background: '#fee2e2',
                        border: 'none',
                        borderRadius: '8px',
                        color: '#dc2626',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: '600'
                      }}
                    >Reset</button>
                  )}
                  <button
                    onClick={() => setShowChat(false)}
                    style={{
                      width: '36px',
                      height: '36px',
                      background: '#f3f4f6',
                      border: 'none',
                      borderRadius: '10px',
                      color: '#6b7280',
                      cursor: 'pointer',
                      fontSize: '18px'
                    }}
                  >✕</button>
                </div>
              </div>

              {/* Chat Messages */}
              <div style={{
                flex: 1,
                overflow: 'auto',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}>
                {chatMessages.length === 0 && (
                  <div style={{
                    padding: '20px',
                    background: '#f3f4f6',
                    borderRadius: '16px',
                    color: '#374151',
                    fontSize: '15px',
                    lineHeight: '1.6'
                  }}>
                    👋 Hi! Tell me what you're looking for in a neighborhood.<br/><br/>
                    <strong>Examples:</strong><br/>
                    • "I want somewhere quiet near good schools"<br/>
                    • "Safety and short commute are my priorities"<br/>
                    • "I need lots of restaurants and nightlife"
                  </div>
                )}
                
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      padding: '14px 18px',
                      background: msg.role === 'user' ? '#059669' : '#f3f4f6',
                      color: msg.role === 'user' ? '#fff' : '#374151',
                      borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                      fontSize: '15px',
                      lineHeight: '1.5'
                    }}
                  >
                    {msg.content}
                  </div>
                ))}

                {/* MCQ Options */}
                {currentQuestion && currentQuestion.options && (
                  <div style={{
                    background: '#f9fafb',
                    borderRadius: '16px',
                    padding: '16px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 12px' }}>
                      Select an option:
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {currentQuestion.options.map((opt, index) => {
                        // Handle both string array and object array formats
                        const optionId = typeof opt === 'string' ? opt : opt.id;
                        const optionLabel = typeof opt === 'string' ? opt : opt.label;
                        const isSelected = selectedOptions.includes(optionId);
                        
                        return (
                          <button
                            key={index}
                            onClick={() => handleOptionSelect(optionId)}
                            style={{
                              padding: '12px 16px',
                              background: isSelected ? '#ecfdf5' : '#fff',
                              border: isSelected ? '2px solid #059669' : '1px solid #e5e7eb',
                              borderRadius: '10px',
                              textAlign: 'left',
                              cursor: 'pointer',
                              fontSize: '14px',
                              color: '#374151',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            {isSelected ? '✓ ' : ''}{optionLabel}
                          </button>
                        );
                      })}
                    </div>
                    <button
                      onClick={submitOptions}
                      disabled={selectedOptions.length === 0 || isLoading}
                      style={{
                        width: '100%',
                        marginTop: '12px',
                        padding: '12px',
                        background: selectedOptions.length > 0 ? '#059669' : '#e5e7eb',
                        border: 'none',
                        borderRadius: '10px',
                        color: selectedOptions.length > 0 ? '#fff' : '#9ca3af',
                        fontSize: '15px',
                        fontWeight: '600',
                        cursor: selectedOptions.length > 0 ? 'pointer' : 'not-allowed'
                      }}
                    >
                      {isLoading ? 'Processing...' : 'Continue →'}
                    </button>
                  </div>
                )}

                {isLoading && !currentQuestion && (
                  <div style={{ 
                    padding: '14px 18px', 
                    background: '#f3f4f6', 
                    borderRadius: '18px',
                    color: '#6b7280',
                    fontSize: '14px'
                  }}>
                    Thinking...
                  </div>
                )}
              </div>

              {/* Chat Input - Only show if no current MCQ question */}
              {!currentQuestion && (
                <div style={{
                  padding: '16px 20px',
                  borderTop: '1px solid #e5e7eb',
                  display: 'flex',
                  gap: '12px'
                }}>
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleChat()}
                    placeholder="Describe your ideal neighborhood..."
                    disabled={isLoading}
                    style={{
                      flex: 1,
                      padding: '14px 18px',
                      background: '#f9fafb',
                      border: '1px solid #e5e7eb',
                      borderRadius: '12px',
                      fontSize: '15px',
                      outline: 'none'
                    }}
                  />
                  <button
                    onClick={handleChat}
                    disabled={isLoading || !chatInput.trim()}
                    style={{
                      width: '48px',
                      background: chatInput.trim() ? '#059669' : '#e5e7eb',
                      border: 'none',
                      borderRadius: '12px',
                      color: chatInput.trim() ? '#fff' : '#9ca3af',
                      fontSize: '20px',
                      cursor: chatInput.trim() ? 'pointer' : 'not-allowed'
                    }}
                  >→</button>
                </div>
              )}
            </div>
          )}

          {/* DETAIL PANEL */}
          {selectedNeighborhood && (
            <div style={{
              position: 'absolute',
              top: '20px',
              right: '24px',
              width: '360px',
              padding: '28px',
              background: '#fff',
              borderRadius: '20px',
              boxShadow: '0 8px 40px rgba(0,0,0,0.12)',
              border: '1px solid #e5e7eb',
              zIndex: 1000
            }}>
              <button 
                onClick={() => setSelectedNeighborhood(null)} 
                style={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                  width: '36px',
                  height: '36px',
                  background: '#f3f4f6',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#6b7280',
                  cursor: 'pointer',
                  fontSize: '18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >✕</button>

              <h3 style={{ fontSize: '26px', fontWeight: '700', color: '#1f2937', margin: '0 0 4px' }}>
                {selectedNeighborhood.name}
              </h3>
              <p style={{ fontSize: '16px', color: '#6b7280', margin: '0 0 24px' }}>
                {selectedNeighborhood.borough}
              </p>

              {/* BIG SCORE */}
              <div style={{
                textAlign: 'center',
                padding: '28px',
                background: '#ecfdf5',
                borderRadius: '16px',
                marginBottom: '24px'
              }}>
                <div style={{
                  fontSize: '64px',
                  fontWeight: '800',
                  color: '#059669',
                  lineHeight: 1
                }}>
                  {(calculateScore(selectedNeighborhood.scores, userWeights) * 100).toFixed(1)}
                </div>
                <div style={{ fontSize: '16px', color: '#6b7280', marginTop: '8px' }}>Match Score</div>
              </div>

              {/* Score breakdown */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
                {Object.entries(selectedNeighborhood.scores).map(([key, value]) => (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '18px', width: '28px' }}>{weightConfig[key]?.icon || '📊'}</span>
                    <span style={{ fontSize: '15px', color: '#6b7280', width: '90px' }}>
                      {weightConfig[key]?.label || key}
                    </span>
                    <div style={{ 
                      flex: 1, 
                      height: '10px', 
                      background: '#e5e7eb', 
                      borderRadius: '5px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${value * 100}%`,
                        height: '100%',
                        background: '#059669',
                        borderRadius: '5px'
                      }} />
                    </div>
                    <span style={{ 
                      fontSize: '15px', 
                      color: '#1f2937', 
                      fontWeight: '600', 
                      width: '40px', 
                      textAlign: 'right' 
                    }}>
                      {(value * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>

              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                paddingTop: '20px', 
                borderTop: '1px solid #e5e7eb' 
              }}>
                <div>
                  <div style={{ fontSize: '14px', color: '#6b7280' }}>Avg. Rent</div>
                  <div style={{ fontSize: '24px', fontWeight: '700', color: '#1f2937' }}>
                    ${selectedNeighborhood.rent.toLocaleString()}/mo
                  </div>
                </div>
                <button style={{
                  padding: '14px 28px',
                  background: '#059669',
                  border: 'none',
                  borderRadius: '12px',
                  color: '#fff',
                  fontSize: '16px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}>
                  View Listings
                </button>
              </div>
            </div>
          )}
        </div>

        {/* LISTINGS PANEL */}
        <div style={{
          width: '420px',
          background: '#fff',
          borderLeft: '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{ 
            padding: '28px 24px 20px', 
            borderBottom: '1px solid #e5e7eb',
            background: '#fff'
          }}>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#1f2937', margin: '0 0 4px' }}>
              {backendResults ? '🎯 Your Top Matches' : 'Top Matches'}
            </h2>
            <p style={{ fontSize: '15px', color: '#6b7280', margin: 0 }}>
              {backendResults 
                ? `${sortedNeighborhoods.length} AI-personalized recommendations`
                : `${sortedNeighborhoods.length} neighborhoods in your budget`}
            </p>
          </div>

          <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
            {sortedNeighborhoods.map((hood, index) => {
              const isHovered = hoveredCard === hood.id;
              const isSelected = selectedNeighborhood?.id === hood.id;
              
              return (
                <div
                  key={hood.id}
                  onClick={() => setSelectedNeighborhood(hood)}
                  onMouseEnter={() => setHoveredCard(hood.id)}
                  onMouseLeave={() => setHoveredCard(null)}
                  style={{
                    padding: '20px',
                    marginBottom: '12px',
                    background: isSelected ? '#ecfdf5' : isHovered ? '#f9fafb' : '#fff',
                    borderRadius: '16px',
                    border: isSelected ? '2px solid #059669' : '1px solid #e5e7eb',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isHovered ? '0 4px 16px rgba(0,0,0,0.06)' : 'none'
                  }}
                >
                  {/* Top row */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    {index === 0 ? (
                      <div style={{
                        background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                        color: '#fff',
                        padding: '6px 14px',
                        borderRadius: '8px',
                        fontSize: '13px',
                        fontWeight: '700',
                        boxShadow: '0 2px 8px rgba(245, 158, 11, 0.3)'
                      }}>
                        🏆 #1 Top Match
                      </div>
                    ) : index === 1 ? (
                      <div style={{
                        background: '#e5e7eb',
                        color: '#4b5563',
                        padding: '5px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>🥈 #2</div>
                    ) : index === 2 ? (
                      <div style={{
                        background: '#fef3c7',
                        color: '#92400e',
                        padding: '5px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>🥉 #3</div>
                    ) : (
                      <div style={{
                        background: '#f3f4f6',
                        color: '#6b7280',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>#{index + 1}</div>
                    )}

                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '32px', fontWeight: '800', color: '#059669', lineHeight: 1 }}>
                        {(hood.totalScore * 100).toFixed(1)}
                      </div>
                      <div style={{ fontSize: '13px', color: '#9ca3af' }}>match</div>
                    </div>
                  </div>

                  <h4 style={{ fontSize: '20px', fontWeight: '700', color: '#1f2937', margin: '0 0 4px' }}>
                    {hood.name}
                  </h4>
                  <p style={{ fontSize: '15px', color: '#6b7280', margin: '0 0 16px' }}>
                    {hood.borough}
                  </p>

                  <div style={{ display: 'flex', gap: '20px', paddingTop: '16px', borderTop: '1px solid #f3f4f6' }}>
                    <div>
                      <div style={{ fontSize: '13px', color: '#9ca3af' }}>Avg. Rent</div>
                      <div style={{ fontSize: '18px', fontWeight: '700', color: '#1f2937' }}>
                        ${hood.rent.toLocaleString()}/mo
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', color: '#9ca3af' }}>Listings</div>
                      <div style={{ fontSize: '18px', fontWeight: '700', color: '#1f2937' }}>
                        {hood.listings}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
