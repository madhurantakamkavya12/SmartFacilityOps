import fs from 'node:fs/promises';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const out='G:/SmartFacilityOps/deliverables/FacilityOps_Milestone1_Overview.pptx';
const p=Presentation.create({slideSize:{width:1280,height:720}});
const slides=[
['Agentic FacilityOps AI Platform','Milestone 1 | Energy Intelligence and Monitoring','A prototype for turning meter readings into useful facility energy insights'],
['Problem Statement','Facility teams receive large volumes of meter and equipment readings. Raw readings make it difficult to spot high consumption, peak demand, missing data, and issues that need review.','This project demonstrates a simple way to turn those readings into clear operational information.'],
['Project Objective','Build an energy monitoring prototype that processes electricity data, calculates useful metrics, forecasts hourly demand, and presents explainable recommendations.','Milestone 1 focuses on energy intelligence. Water readings are included only for data-quality review.'],
['Dataset','Source: iAWE, collected from a home in New Delhi.','Electricity: channels 1 and 2 are mains; channels 4 and 5 are air conditioners. Readings include timestamps and power in watts. Water: meter ID, timestamp, and binary state. Analysis window: July 13 to August 4, 2013.'],
['Technologies and Architecture','Python and Pandas process and analyse data. SQLite stores structured meter readings and review alerts. LangGraph organizes analysis followed by recommendations. Streamlit presents the dashboard; Plotly draws interactive charts.','The workflow is local and does not call a large language model.'],
['Code and Data Flow','Raw iAWE files → compare_ac.py cleans and aggregates readings → setup_database.py loads readings into SQLite → database.py supplies data → energy_agent.py calculates metrics and recommendations → dashboard.py presents results.','forecast_energy.py creates and evaluates the hourly historical-average baseline. Water profiling scripts validate the water signal separately.'],
['Dashboard Demo and Results','Show KPI cards, historical load, next-day forecast, recommendations, water signal quality, and downloadable report.','360.46 kWh mains energy | 121.52 kWh for both ACs | 33.7% AC share | 97.9% mains coverage | 5,401.4 W peak mains power | 212 consistency review flags (0.65%).','Forecast holdout: 20 covered hours; MAE 0.312 kW; RMSE 0.508 kW.'],
['Anomaly Detection Limitation','A rule flags minutes where combined AC power exceeds combined mains power. It produced 212 review flags. These flags are not confirmed faults.','The iAWE data has no labelled anomaly examples, so the 85% accuracy target cannot be verified. We do not claim measured anomaly accuracy.'],
['Future Scope','Evaluate anomaly detection with labelled fault data or expert-confirmed labels. Connect real facility electricity, HVAC, occupancy, and maintenance data. Validate recommendation thresholds with facility engineers. Extend beyond a local prototype after security and deployment requirements are defined.'],
];
for(let i=0;i<slides.length;i++){
 const s=p.slides.add(); s.background.fill='#FFFFFF';
 s.shapes.add({geometry:'rect',position:{left:0,top:0,width:1280,height:16},fill:'#F28C28',line:{fill:'none',width:0}});
 const title=s.shapes.add({geometry:'textbox',position:{left:84,top:64,width:1112,height:68},fill:'none',line:{fill:'none',width:0}}); title.text=slides[i][0]; title.text.style={fontFamily:'Aptos',fontSize:38,bold:true,color:'#E87517',alignment:'left',verticalAlignment:'middle'};
 s.shapes.add({geometry:'rect',position:{left:84,top:146,width:90,height:5},fill:'#F28C28',line:{fill:'none',width:0}});
 const body=s.shapes.add({geometry:'textbox',position:{left:92,top:190,width:1088,height:400},fill:'none',line:{fill:'none',width:0}}); body.text=slides[i].slice(1).join('\n\n'); body.text.style={fontFamily:'Aptos',fontSize:24,color:'#333333',alignment:'left',verticalAlignment:'top'};
 const page=s.shapes.add({geometry:'textbox',position:{left:1100,top:654,width:96,height:28},fill:'none',line:{fill:'none',width:0}}); page.text=`${i+1} / ${slides.length}`; page.text.style={fontFamily:'Aptos',fontSize:14,color:'#777777',alignment:'right'};
 s.speakerNotes.text=`Presenter notes: ${slides[i].slice(1).join(' ')}`;
}
const file=await PresentationFile.exportPptx(p); await file.save(out);
