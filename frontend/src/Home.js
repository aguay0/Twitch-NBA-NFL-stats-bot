import React from 'react'
import "./Home.css";
import { Link } from 'react-router-dom';

function Home() {
  return (
    <div className="login">
        <img className="home_image" src="https://c4.wallpaperflare.com/wallpaper/923/905/283/anime-one-piece-franky-one-piece-robot-wallpaper-preview.jpg" />
        <div className="login_container">
            <h5>Live NBA & NFL Twitch Stats Bot</h5>
            <p>Realtime NBA & NFL player stats in your twitch chat. </p>
            <Link to="http://localhost:4343/oauth/callback">
                <button className="twitch_login">Login with Twitch</button>
            </Link>
            <p>Login required to authenticate your twitch account to the bot.</p>
        </div>
    </div>
  )
}

export default Home