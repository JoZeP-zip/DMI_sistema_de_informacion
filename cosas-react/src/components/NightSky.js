import React, { useEffect, useMemo, useState } from "react";
import "./NightSky.css";
import ShootingStar from "./ShootingStar";

const NightSky = () => {

  // Partículas metálicas
  const stars = useMemo(() => {
    return Array.from({ length: 260 }, (_, i) => ({
      id: i,
      top: Math.random() * 100,
      left: Math.random() * 100,
      size: Math.random() * 2.5 + 1,
      delay: Math.random() * 6,
      duration: 4 + Math.random() * 5,
      glowDelay: Math.random() * 8,
      glowTime: 2 + Math.random() * 4,
    }));
  }, []);

  const [shootingStars, setShootingStars] = useState([]);

  const [mouse, setMouse] = useState({
    x: 50,
    y: 50,
  });

  /* ===========================
     CHISPAS
  ============================ */

  useEffect(() => {

    let timeout;

    const createSpark = () => {

      const id = Date.now() + Math.random();

      const startX = Math.random() * 100;
      const startY = Math.random() * 100;

      const angle = 315;

      const spark = {

        id,

        style:{

          top:`${startY}%`,

          left:`${startX}%`,

          "--angle":`${angle}deg`,

          animationDuration:`${3 + Math.random()*2}s`

        }

      };

      setShootingStars(prev=>[...prev,spark]);

      setTimeout(()=>{

        setShootingStars(prev=>

          prev.filter(item=>item.id!==id)

        );

      },5000);

      timeout=setTimeout(

        createSpark,

        120 + Math.random()*350

      );

    };

    createSpark();

    return()=>clearTimeout(timeout);

  },[]);



  /* ===========================
      MOUSE
  ============================ */

  useEffect(()=>{

    const move=(e)=>{

      setMouse({

        x:(e.clientX/window.innerWidth)*100,

        y:(e.clientY/window.innerHeight)*100

      });

    };

    window.addEventListener("mousemove",move);

    return()=>window.removeEventListener("mousemove",move);

  },[]);



  return (

    <div

      id="night-sky"

      style={{

        "--mouse-x":`${mouse.x}%`,

        "--mouse-y":`${mouse.y}%`

      }}

    >

      {/* Partículas */}

      {stars.map(star=>(

        <span

          key={star.id}

          className="star"

          style={{

            top:`${star.top}%`,

            left:`${star.left}%`,

            width:`${star.size}px`,

            height:`${star.size}px`,

            animationDelay:`${star.delay}s, ${star.glowDelay}s`,

            animationDuration:`${star.duration}s, ${star.glowTime}s`,

            "--glow-delay":`${star.glowDelay}s`,

            "--glow-time":`${star.glowTime}s`

          }}

        />

      ))}



      {/* Chispas */}

      {shootingStars.map(star=>(

        <ShootingStar

          key={star.id}

          style={star.style}

        />

      ))}

    </div>

  );

};

export default NightSky;