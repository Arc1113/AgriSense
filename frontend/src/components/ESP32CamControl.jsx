import {
    ArrowBack,
    ArrowForward,
    CenterFocusStrong,
    ControlCamera,
    FiberManualRecord,
    Home,
    KeyboardArrowDown,
    KeyboardArrowLeft,
    KeyboardArrowRight,
    KeyboardArrowUp,
    LinearScale,
    MyLocation,
    RotateLeft,
    RotateRight,
    Speed,
    Stop,
    ThreeSixty,
    Tune,
    Videocam,
    VideocamOff,
    ViewInAr,
    Wifi,
    WifiOff
} from '@mui/icons-material';
import {
    Alert,
    alpha,
    Box,
    Button,
    ButtonGroup,
    Chip,
    CircularProgress,
    Divider,
    Grid,
    IconButton,
    Paper,
    Slider,
    Stack,
    Tooltip,
    Typography,
    useTheme
} from '@mui/material';
import axios from 'axios';
import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = import.meta.env?.VITE_API_URL || 'http://localhost:8000';

// --- Control Button Component ---
const ControlBtn = ({ icon, label, onClick, onMouseDown, onMouseUp, color = 'primary', size = 'medium', disabled = false, sx = {} }) => (
  <Tooltip title={label} arrow placement="top">
    <span>
      <IconButton
        onClick={onClick}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        color={color}
        disabled={disabled}
        size={size}
        sx={{
          bgcolor: (theme) => alpha(theme.palette[color]?.main || theme.palette.primary.main, 0.08),
          border: '1px solid',
          borderColor: (theme) => alpha(theme.palette[color]?.main || theme.palette.primary.main, 0.2),
          '&:hover': {
            bgcolor: (theme) => alpha(theme.palette[color]?.main || theme.palette.primary.main, 0.18),
            transform: 'scale(1.08)',
          },
          '&:active': {
            transform: 'scale(0.95)',
          },
          transition: 'all 0.15s ease',
          ...sx,
        }}
      >
        {icon}
      </IconButton>
    </span>
  </Tooltip>
);

// --- Section Header ---
const SectionHeader = ({ icon, title, subtitle }) => (
  <Box sx={{ mb: 1.5 }}>
    <Stack direction="row" alignItems="center" spacing={1}>
      {icon}
      <Typography variant="subtitle1" fontWeight={700} color="text.primary">
        {title}
      </Typography>
    </Stack>
    {subtitle && (
      <Typography variant="caption" color="text.secondary" sx={{ ml: 4 }}>
        {subtitle}
      </Typography>
    )}
  </Box>
);

const ESP32CamControl = () => {
  const theme = useTheme();
  const [state, setState] = useState({
    pan_angle: 90,
    tilt_angle: 90,
    linear_position: 50,
    rail_moving: false,
    rail_direction: 'stop',
    rail_speed: 0,
    connected: false,
  });
  const [railSpeed, setRailSpeed] = useState(150);
  const [panTiltStep, setPanTiltStep] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streamActive, setStreamActive] = useState(false);
  const [streamUrl, setStreamUrl] = useState('');
  const holdInterval = useRef(null);

  // --- Fetch status ---
  const fetchStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/robot/status`);
      if (res.data?.state) setState(res.data.state);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // --- Fetch stream URL ---
  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/robot/stream-url`);
        setStreamUrl(res.data.stream_url);
      } catch {
        setStreamUrl('');
      }
    })();
  }, []);

  // --- API helpers ---
  const sendCommand = async (endpoint, data = {}, method = 'post') => {
    setLoading(true);
    setError(null);
    try {
      const res = method === 'get'
        ? await axios.get(`${API_BASE}${endpoint}`)
        : await axios.post(`${API_BASE}${endpoint}`, data);
      if (res.data?.state) setState(res.data.state);
      return res.data;
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Command failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // --- Linear rail ---
  const moveRail = (direction) => sendCommand('/api/robot/linear/move', { direction, speed: railSpeed });
  const stopRail = () => sendCommand('/api/robot/linear/stop');

  // Hold-to-move for rail
  const startRailHold = (direction) => {
    moveRail(direction);
    holdInterval.current = setInterval(() => moveRail(direction), 300);
  };
  const stopRailHold = () => {
    clearInterval(holdInterval.current);
    stopRail();
  };

  // --- Pan-tilt ---
  const setPanTilt = (pan, tilt) => sendCommand('/api/robot/pantilt/set', { pan, tilt });
  const incrementPanTilt = (axis, direction) =>
    sendCommand('/api/robot/pantilt/increment', { axis, direction, increment: panTiltStep });
  const homePanTilt = () => sendCommand('/api/robot/pantilt/home');

  // --- Presets ---
  const moveToPreset = (preset) => sendCommand('/api/robot/preset', { preset });

  // --- Home all ---
  const homeAll = () => sendCommand('/api/robot/home', { home_rail: true, home_pan_tilt: true });

  const isConnected = state.connected;

  return (
    <Box sx={{ width: '100%', maxWidth: 1200, mx: 'auto' }}>
      {/* Connection & Status Bar */}
      <Paper
        elevation={0}
        sx={{
          mb: 2,
          p: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
          bgcolor: isConnected
            ? alpha(theme.palette.success.main, 0.06)
            : alpha(theme.palette.error.main, 0.06),
          border: '1px solid',
          borderColor: isConnected
            ? alpha(theme.palette.success.main, 0.25)
            : alpha(theme.palette.error.main, 0.25),
          borderRadius: 2,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Chip
            icon={isConnected ? <Wifi /> : <WifiOff />}
            label={isConnected ? 'ESP32 Connected' : 'ESP32 Disconnected'}
            color={isConnected ? 'success' : 'error'}
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<FiberManualRecord sx={{ fontSize: 10 }} />}
            label={`Pan: ${state.pan_angle}°`}
            size="small"
            variant="outlined"
          />
          <Chip
            icon={<FiberManualRecord sx={{ fontSize: 10 }} />}
            label={`Tilt: ${state.tilt_angle}°`}
            size="small"
            variant="outlined"
          />
          <Chip
            icon={<LinearScale sx={{ fontSize: 14 }} />}
            label={`Rail: ${state.linear_position}%`}
            size="small"
            variant="outlined"
          />
        </Stack>
        <Stack direction="row" spacing={1}>
          {loading && <CircularProgress size={20} />}
          <Button
            size="small"
            variant="outlined"
            startIcon={<Home />}
            onClick={homeAll}
            color="secondary"
          >
            Home All
          </Button>
        </Stack>
      </Paper>

      {error && (
        <Alert severity="warning" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {/* ===================== LEFT: Video Feed ===================== */}
        <Grid item xs={12} md={7}>
          <Paper
            elevation={2}
            sx={{
              borderRadius: 3,
              overflow: 'hidden',
              position: 'relative',
              bgcolor: '#111',
              minHeight: 380,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {streamActive && streamUrl ? (
              <img
                src={streamUrl}
                alt="ESP32-CAM Stream"
                style={{ width: '100%', height: '100%', objectFit: 'contain', maxHeight: 450 }}
                onError={() => setStreamActive(false)}
              />
            ) : (
              <Box sx={{ textAlign: 'center', py: 6, px: 3 }}>
                <VideocamOff sx={{ fontSize: 64, color: 'grey.600', mb: 2 }} />
                <Typography variant="h6" color="grey.500">
                  Camera Stream Inactive
                </Typography>
                <Typography variant="body2" color="grey.600" sx={{ mt: 0.5, mb: 2 }}>
                  Click below to start the ESP32-CAM live feed
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Videocam />}
                  onClick={() => setStreamActive(true)}
                  color="primary"
                  size="large"
                  sx={{ borderRadius: 2, px: 4, textTransform: 'none', fontWeight: 600 }}
                >
                  Start Camera Stream
                </Button>
              </Box>
            )}

            {/* Overlay controls on video */}
            {streamActive && (
              <Box
                sx={{
                  position: 'absolute',
                  bottom: 12,
                  left: 12,
                  right: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Chip
                  icon={<FiberManualRecord sx={{ fontSize: 10, color: 'error.main' }} />}
                  label="LIVE"
                  size="small"
                  sx={{ bgcolor: 'rgba(0,0,0,0.6)', color: '#fff', fontWeight: 700 }}
                />
                <Button
                  size="small"
                  variant="contained"
                  color="error"
                  startIcon={<Stop />}
                  onClick={() => setStreamActive(false)}
                  sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600, minWidth: 0 }}
                >
                  Stop
                </Button>
              </Box>
            )}
          </Paper>

          {/* Quick Presets */}
          <Paper elevation={1} sx={{ mt: 2, p: 2, borderRadius: 3 }}>
            <SectionHeader
              icon={<MyLocation color="primary" fontSize="small" />}
              title="Quick Presets"
              subtitle="Jump to predefined camera positions"
            />
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {[
                { key: 'home', label: 'Home', icon: <Home fontSize="small" /> },
                { key: 'left_scan', label: 'Scan Left', icon: <KeyboardArrowLeft fontSize="small" /> },
                { key: 'right_scan', label: 'Scan Right', icon: <KeyboardArrowRight fontSize="small" /> },
                { key: 'top_view', label: 'Top View', icon: <KeyboardArrowUp fontSize="small" /> },
                { key: 'bottom_view', label: 'Bottom View', icon: <KeyboardArrowDown fontSize="small" /> },
                { key: 'full_left', label: 'Full Left', icon: <RotateLeft fontSize="small" /> },
                { key: 'full_right', label: 'Full Right', icon: <RotateRight fontSize="small" /> },
              ].map((p) => (
                <Button
                  key={p.key}
                  size="small"
                  variant="outlined"
                  startIcon={p.icon}
                  onClick={() => moveToPreset(p.key)}
                  sx={{
                    borderRadius: 2,
                    textTransform: 'none',
                    fontWeight: 500,
                    px: 1.5,
                    fontSize: '0.8rem',
                  }}
                >
                  {p.label}
                </Button>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* ===================== RIGHT: Controls ===================== */}
        <Grid item xs={12} md={5}>
          <Stack spacing={2}>
            {/* --- Linear Rail Control --- */}
            <Paper elevation={1} sx={{ p: 2.5, borderRadius: 3 }}>
              <SectionHeader
                icon={<LinearScale color="primary" fontSize="small" />}
                title="Linear Rail"
                subtitle="Rack & pinion / belt drive — move camera left-right"
              />

              {/* Rail visual indicator */}
              <Box sx={{ px: 1, mb: 2 }}>
                <Box
                  sx={{
                    position: 'relative',
                    height: 8,
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    borderRadius: 4,
                    overflow: 'visible',
                  }}
                >
                  <Box
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      left: `${state.linear_position}%`,
                      transform: 'translate(-50%, -50%)',
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      bgcolor: state.rail_moving ? 'warning.main' : 'primary.main',
                      border: '3px solid #fff',
                      boxShadow: 2,
                      transition: 'left 0.3s ease',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">Left</Typography>
                  <Typography variant="caption" color="text.secondary">{state.linear_position}%</Typography>
                  <Typography variant="caption" color="text.secondary">Right</Typography>
                </Box>
              </Box>

              {/* Rail buttons */}
              <Stack direction="row" justifyContent="center" alignItems="center" spacing={2} sx={{ mb: 2 }}>
                <ControlBtn
                  icon={<ArrowBack />}
                  label="Move Left (hold)"
                  onMouseDown={() => startRailHold('left')}
                  onMouseUp={stopRailHold}
                  color="primary"
                />
                <ControlBtn
                  icon={<Stop />}
                  label="Stop Rail"
                  onClick={stopRail}
                  color="error"
                  sx={{ width: 52, height: 52 }}
                />
                <ControlBtn
                  icon={<ArrowForward />}
                  label="Move Right (hold)"
                  onMouseDown={() => startRailHold('right')}
                  onMouseUp={stopRailHold}
                  color="primary"
                />
              </Stack>

              {/* Speed slider */}
              <Stack direction="row" spacing={2} alignItems="center">
                <Speed fontSize="small" color="action" />
                <Slider
                  value={railSpeed}
                  onChange={(_, v) => setRailSpeed(v)}
                  min={50}
                  max={255}
                  step={5}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}`}
                  size="small"
                  sx={{ flex: 1 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 30 }}>
                  {railSpeed}
                </Typography>
              </Stack>
            </Paper>

            {/* --- Pan-Tilt Control --- */}
            <Paper elevation={1} sx={{ p: 2.5, borderRadius: 3 }}>
              <SectionHeader
                icon={<ControlCamera color="secondary" fontSize="small" />}
                title="Pan & Tilt"
                subtitle="Rotate camera and adjust viewing angle"
              />

              {/* D-Pad Style Pan-Tilt Controls */}
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: 'auto auto auto',
                  gridTemplateRows: 'auto auto auto',
                  gap: 0.5,
                  justifyContent: 'center',
                  alignItems: 'center',
                  mb: 2,
                }}
              >
                {/* Row 1 */}
                <Box />
                <ControlBtn
                  icon={<KeyboardArrowUp sx={{ fontSize: 28 }} />}
                  label="Tilt Up"
                  onClick={() => incrementPanTilt('tilt', 'negative')}
                  color="secondary"
                />
                <Box />

                {/* Row 2 */}
                <ControlBtn
                  icon={<KeyboardArrowLeft sx={{ fontSize: 28 }} />}
                  label="Pan Left"
                  onClick={() => incrementPanTilt('pan', 'negative')}
                  color="secondary"
                />
                <Tooltip title="Home Pan-Tilt" arrow>
                  <span>
                    <IconButton
                      onClick={homePanTilt}
                      sx={{
                        width: 52,
                        height: 52,
                        bgcolor: alpha(theme.palette.secondary.main, 0.12),
                        border: '2px solid',
                        borderColor: alpha(theme.palette.secondary.main, 0.3),
                        '&:hover': { bgcolor: alpha(theme.palette.secondary.main, 0.22) },
                      }}
                    >
                      <CenterFocusStrong color="secondary" />
                    </IconButton>
                  </span>
                </Tooltip>
                <ControlBtn
                  icon={<KeyboardArrowRight sx={{ fontSize: 28 }} />}
                  label="Pan Right"
                  onClick={() => incrementPanTilt('pan', 'positive')}
                  color="secondary"
                />

                {/* Row 3 */}
                <Box />
                <ControlBtn
                  icon={<KeyboardArrowDown sx={{ fontSize: 28 }} />}
                  label="Tilt Down"
                  onClick={() => incrementPanTilt('tilt', 'positive')}
                  color="secondary"
                />
                <Box />
              </Box>

              {/* Pan Slider */}
              <Stack spacing={1.5}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <ThreeSixty fontSize="small" color="action" />
                  <Typography variant="caption" color="text.secondary" sx={{ minWidth: 28 }}>Pan</Typography>
                  <Slider
                    value={state.pan_angle}
                    onChange={(_, v) => setPanTilt(v, state.tilt_angle)}
                    min={0}
                    max={180}
                    step={1}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}°`}
                    size="small"
                    color="secondary"
                    sx={{ flex: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ minWidth: 32 }}>
                    {state.pan_angle}°
                  </Typography>
                </Stack>

                {/* Tilt Slider */}
                <Stack direction="row" spacing={2} alignItems="center">
                  <ViewInAr fontSize="small" color="action" />
                  <Typography variant="caption" color="text.secondary" sx={{ minWidth: 28 }}>Tilt</Typography>
                  <Slider
                    value={state.tilt_angle}
                    onChange={(_, v) => setPanTilt(state.pan_angle, v)}
                    min={0}
                    max={180}
                    step={1}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}°`}
                    size="small"
                    color="secondary"
                    sx={{ flex: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ minWidth: 32 }}>
                    {state.tilt_angle}°
                  </Typography>
                </Stack>
              </Stack>

              {/* Step Size */}
              <Divider sx={{ my: 1.5 }} />
              <Stack direction="row" spacing={2} alignItems="center">
                <Tune fontSize="small" color="action" />
                <Typography variant="caption" color="text.secondary">Step</Typography>
                <ButtonGroup size="small" variant="outlined" color="secondary">
                  {[1, 5, 10, 15, 30].map((s) => (
                    <Button
                      key={s}
                      onClick={() => setPanTiltStep(s)}
                      variant={panTiltStep === s ? 'contained' : 'outlined'}
                      sx={{ minWidth: 36, textTransform: 'none', fontWeight: 600, fontSize: '0.75rem' }}
                    >
                      {s}°
                    </Button>
                  ))}
                </ButtonGroup>
              </Stack>
            </Paper>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ESP32CamControl;
