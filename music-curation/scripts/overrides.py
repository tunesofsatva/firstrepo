R=lambda **kw: None
RENAME={k.lower():v for k,v in {
# English
'2 Brazil!':'To Brazil!','Magenta Riddim DJ Sandy Ut Song':'Magenta Riddim',"k'naan Wavin' Flag":"Wavin' Flag",
'Walk The Moon Vs Pierce Fulton Shut Up And Dance':'Shut Up And Dance','Thoia Thoing Any Me':'Thoia Thoing',
'Follow The Propaganda Sergio Garcia':'Follow The Propaganda','Levels I FBM':'Levels','Drop It On Me 1':'Drop It On Me',
'Get Busy For This PILO boot':'Get Busy For This','Hot Hot Hot Radio':'Hot Hot Hot','Noche de Rumba Maximo Music':'Noche de Rumba',
# Old Hindi
'Aaj Kal Tere Mere Pyar Ke Sabse':'Aaj Kal Tere Mere Pyar Ke','Chahe Koi Mujhe Junglee Kahe DJ Akhil Talreja (Yahoo AT)':'Chahe Koi Mujhe Junglee Kahe',
'Choli Ke Piche X Losing It (Fisher)':'Choli Ke Peeche x Losing It','Duniya Mein Logon Ko DJ Alfaa (.se)':'Duniya Mein Logon Ko',
'Husnn Hai Suhaana x Lets Go (DjZNik)':"Husnn Hai Suhaana x Let's Go",'Jeene Ke Hai Chaar Din':'Jeene Ke Hain Chaar Din',
'Kya Mujhe':'Kya Mujhe Pyaar Hai','Le Gayi':'Le Gayi Le Gayi','Mohabbatein - Aankhein Khuli':'Aankhein Khuli',
'Muqabla Anchor Point':'Muqabla x Anchor Point','Premika Ne Pyar Se Vijay Khathuria':'Premika Ne Pyar Se','Saat Samundar DJ K3O2':'Saat Samundar Paar',
'Tirchi Topi Wale Deejay MHD x Partha & Cherry':'Tirchi Topi Wale','Tumse Milke Dil Kal x Bebot (NYAD)':'Tumse Milke Dil Ka x Bebot',
'Uri Uri Baba Usha Uthup Balidan Rakhee Gulzar, Tapash Pal Bengali Film Song':'Uri Uri Baba','Woh Ladki Hai Kaha':'Woh Ladki Hai Kahan',
'Yaad Aa Raha Hai (VizzKid)':'Yaad Aa Raha Hai','Soni De Dakhre':'Soni De Nakhre','Dola Re':'Dola Re Dola',
'Khaike Pan Banaras Wala (Where I Are)':'Khaike Pan Banaras Wala','Taal':'Taal Se Taal','Badshah':'Baadshah Oh Baadshah',
'Humse Hai Muqabla':'Muqabla','Beedi Jalaile (Mr. Saxobeat)':'Beedi Jalaile x Mr. Saxobeat','Koi Kahe Kehta Rahe':'Koi Kahe',
# New Hindi
'Aapka Kya Hoga (Dhanno) (Housefull)':'Aapka Kya Hoga (Dhanno)','Abhi Toh Party Shuru x Calabria (Mkroove)':'Abhi Toh Party Shuru x Calabria',
'Baaki Baatein Peene Baad (Shameless Mani x Samz)':'Baaki Baatein Peene Baad','Besharam Rang x World Hold On (Mkroove)':'Besharam Rang x World Hold On',
'Bhare Bazzar (DJ Yash Khaira (hearthis.at)':'Bhare Bazaar','Boro Boro (AFTERAll)':'Boro Boro','Desi Boyz x I Know You Want Me (DJCQ)':'Desi Boyz x I Know You Want Me',
'Ek Main Aur Ek Tu':'Ek Main Aur Ekk Tu','FE!N x Garba (DMG Zeus)':'FE!N x Garba','Gallan Goodiyan':'Gallan Goodiyaan','Jamal Kudu[Iranian]':'Jamal Kudu',
'Jhoome Jo Pathan':'Jhoome Jo Pathaan','Love Aaj Kal Saif Ali Khan & Deepika Padukone':'Aahun Aahun (Love Aaj Kal)','Majnuna x Dhan Ta Nan copy':'Majnuna x Dhan Ta Nan',
'Mamta Sharma & Wajid;':'Fevicol Se','Marjaani Song Billu Shahrukh Khan Kareena Kapoor Sukhwinder Singh, Sunidhi Chauhan':'Marjaani (Billu)',
'Patakha Guddi (Eddie G)':'Patakha Guddi','Rang Sky Force Akshay Kumar, Veer P, Sara, Nimrat, Tanishk, Satinder Sartaaj, Zahrah, Shloke':'Rang (Sky Force)',
'Sadi Galing':'Sadi Gali','Saami Saami Tapori':'Saami Saami','Shararat · Shashwat Sachdev · Madhubanti Bagchi · Jasmine Sandlas':'Shararat (Dhurandhar)',
'Suniya Suniya x Eenie Meenie (Magnet x THE Destroyer)':'Suniyan Suniyan x Eenie Meenie','Taambdi Chaamdi Troll Edit Kratex, Shreyas DJ Ravish & DJ Chico':'Taambdi Chaamdi',
'Without Me x Joote Do Paise Lo x O Humdum (Mr Veatz)':'Without Me x Joote Do Paise Lo x O Humdum','Apna Time Aayega X The Time Is Now (John Cena)':'Apna Time Aayega x The Time Is Now',
'Ud Daa Punjab (PrinceMusic)':'Ud Daa Punjab','The Breakup Song (O2SRK & Atharva)':'The Breakup Song','Dil Diya Gallan (Apologise)':'Dil Diya Gallan x Apologize',
'Machayenge x TALA (Tribal Tech)':'Machayenge x TALA',
# Punjabi
'Gur Nalo Ishq (Djcq)':'Gur Nalo Ishq Mitha','Jine Mera Dil Lutiya':'Jine Mera Dil Luteya','Pind De Gerhe':'Pind De Gehre (Meri Kali Activa Da)',
'White Black Brown':'White Brown Black','Na Na Na Nare Daler Mehdi':'Na Na Na Na Re',
'Ikk Hai Ikk Hai Kudi Haryane Val Di Ammy Virk & Sonam Bajwa Avvy Sra':'Kudi Haryane Val Di','Laembadgini Diljit Dosanjh':'Laembadgini',
'Take It Easy x N The Hood (Karan Aujla)':'Take It Easy x N The Hood','Aaye Haaye (Karan Aujla)':'Aaye Haaye','4 Yaar (Parmish Verma)':'4 Yaar',
'Yeah Naah (Karan Aujla)':'Yeah Naah','Obsessed x Le Gayi (Akod)':'Obsessed x Le Gayi','Lak Twent Eight Kudi Da':'Lak 28 Kudi Da',
# Tamil
"Don'u Don'u Don'u - The Don's Romance":"Don'u Don'u Don'u",'Mambazhamam Mambazham Song Pokkiri Vijay Manisharma Asin':'Mambazhamaam (Pokkiri)',
'Pathala Pathala Lyric Kamal Haasan Vijay Sethupathi Lokesh Kanagaraj Anirudh':'Pathala Pathala (Vikram)','Dhee - Enjoy Enjaami':'Enjoy Enjaami',
'They Not Like Us X Maari':'Not Like Us x Maari','Vaathi Coming Remix':'Vaathi Coming','Nakka Mukka':'Naaka Mukka',
'Watermelon Sugar x Master The Blaster (Xire)':'Watermelon Sugar x Master The Blaster',
# Telugu
'Full Video: Nallanchu Thellacheera Mr Bachchan Ravi Teja, Bhagyashri Mickey J Meyer Harish S':'Nallanchu Thellacheera (Mr. Bachchan)',
'దావూదీ Lyrical Video Song Devara NTR Janhvi Kapoor Koratala Siva Anirudh':'Daavudi (Devara)',
'Family Party 4K MCA Video Songs Nani Sai Pallavi DSP Dil Raju Mango Music':'Family Party (MCA)',
'Nuvvante Naku Chala Istame Nithiin, Adah Sharma':'Nuvvante Naku Chala Istame (Heart Attack)',
'Rowdy Baby Dhanush, Sai Pallavi Yuvan Shankar Raja Balaji Mohan':'Rowdy Baby (Telugu)',
'Mirchi Songs Yahoon Yahoon Latest Telugu Video Songs Prabhas, Richa':'Yahoon Yahoon (Mirchi)',
'Rama Loves Seeta Vinaya Vidheya Rama Ram Charan, Kiara Advani, Vivek Oberoi':'Rama Loves Seeta (Vinaya Vidheya Rama)',
'Reddy Ikkada Soodu - Full Video Aravindha Sametha Jr. NTR, Pooja Hegde Thaman S':'Reddy Ikkada Soodu (Aravindha Sametha)',
'Sarrainodu Sarrainodu Allu Arjun, Rakul Preet Telugu Songs':'Sarrainodu (Title Song)',
'Ramuloo Ramulaa Allu Arjun Trivikram Thaman S AA19':'Ramuloo Ramulaa (Ala Vaikunthapurramuloo)','Oo Antava Mawa':'Oo Antava',
'Masterpiece Annange Love Aagidhe Video Song Yash Shanvi V Harikrishna Manju Mandavya':'Annange Love Aagidhe (Masterpiece)',
'Blockbuster Sarrainodu Allu Arjun, Rakul Preet Telugu Songs':'Blockbuster (Sarrainodu)',
# Kannada
'ALL OK Maramman Disco Tanya Hope Tennis Krishna (Allok Tanyahope Tenniskrishna)':'Maramma Disco',
'Bangle Bangari EKKA Yuva Rajkumar Rohit Padaki Charan raj Sanjana Anand':'Bangle Bangari (Ekka)',
'Ekka Raja Rani Video Puneeth Rajkumar Kailash Kher V.Harikrishna Yogaraj Bhat Suri':'Ekka Raja Rani',
'Nanda Loves Nanditha I Jinke Marina Audio Song I Yogesh ,Nanditha I Akshaya Audio':'Jinke Marina (Nanda Loves Nanditha)',
'Enne Namdu Oota Nimdu':'Enne Namdu','Ra Ra Rakkama':'Ra Ra Rakkamma','Uppigintha Ruchi':'Uppiginta Ruchi Bere Illa',
'En Madbeku - From "Suthradaari"':'En Madbeku (Suthradaari)','Shakuntala Shake Your Body Please - From "Trivikrama"':'Shakuntala Shake Your Body Please',
'Baava - Theme Song':'Baava Theme (Su From So)','3 PEG - Kannada Rapper Chandan Shetty Aindrita Ray ft.Vijeth':'3 Peg',
}.items()}
DROP={x.lower() for x in [
 'DJ Ravish x DJ Chico & DJ Bapu','Samz','Ni**as In Paris','Wake Me Up When September Ends','Chasing Cars Vs Time After Time','Baby Shark',
 'Incomplete','Night Changes','RANG DE Basanti full','Shameless Mani Skelltron','Mundiyan Pan Jabi','Kaho Na Pyar Hai x Kejirwal',
 'With You','Titliaan','Bheegi Si Bhaagi Si','Heeriye','Maiyya Mainu (Jersey)','Hayyoda','Un Mela Aasadhaan','Tamil|Not Like Us',
 'NewHindi|Kala Chasma','OldHindi|Kala Chasma']}
MOVE={k.lower():v for k,v in {
 'OldHindi|Uff Teri Adaa':'NewHindi','Toxic':'Punjabi','No Love':'Punjabi','No Love x Fogo':'Punjabi','Summer High':'Punjabi','Summer High x Levels':'Punjabi',
 'By My Side X Closer':'Punjabi','Baller x Stop Snitchin x Voices':'Punjabi','Tere Bina Na Guzara x Eenie Meenie':'Punjabi',
 'Suniyan Suniyan':'Punjabi','Suniyan Suniyan x Eenie Meenie':'Punjabi','Suniyan Suniyan x Nobody Like You':'Punjabi',
 'Annange Love Aagidhe (Masterpiece)':'Kannada'}.items()}
