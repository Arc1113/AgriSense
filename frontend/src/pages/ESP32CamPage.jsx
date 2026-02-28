import { Home as HomeIcon, NavigateNext, Videocam } from '@mui/icons-material';
import { Box, Breadcrumbs, Container, Link, Stack, Typography } from '@mui/material';
import ESP32CamControl from '../components/ESP32CamControl';

const ESP32CamPage = () => {
  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 1 }}>
          <Link underline="hover" color="inherit" href="/" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <HomeIcon fontSize="small" />
            Dashboard
          </Link>
          <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Videocam fontSize="small" />
            ESP32-CAM Control
          </Typography>
        </Breadcrumbs>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Videocam sx={{ fontSize: 32, color: 'primary.main' }} />
          <Box>
            <Typography variant="h5" fontWeight={700} color="text.primary">
              ESP32-CAM Robot Control
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Control linear rail movement, pan-tilt camera positioning, and live video stream
            </Typography>
          </Box>
        </Stack>
      </Box>

      {/* Main Control Panel */}
      <ESP32CamControl />
    </Container>
  );
};

export default ESP32CamPage;
