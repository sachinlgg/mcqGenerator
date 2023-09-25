import * as React from 'react';
import { Link } from 'react-router-dom';

import { Box, Typography } from '@mui/material';
import Move from '../shared/Move';
import logo from '../img/logo.png';

export default function ApplicationHeaderLogo() {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        flexDirection: 'row'
      }}>
      <Link to="/" className="logo-link">
        <Move rotation={0} timing={2000} scale={1.2} springConfig={{ tension: 150, friction: 5 }}>
          <img alt="Incident Bot" src={logo} style={{ width: '35px', height: '35px' }} />
        </Move>
      </Link>
      <Typography
        variant="h7"
        sx={{
          fontFamily: 'Roboto',
          fontWeight: 500,
          letterSpacing: '.1rem',
          marginLeft: 2,
          marginTop: 0.5
        }}>
        INCIDENT BOT
      </Typography>
    </Box>
  );
}
